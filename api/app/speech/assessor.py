import base64
import json
import struct
from typing import Any, Protocol

import httpx

from app.domain.cost import Metered
from app.domain.pronunciation import Assessment, WordScore
from app.llm.grader import ProviderUnavailableError

# Short-audio recognition takes the reference text in a header and scores it word by word.
WAV_MIME = "audio/wav; codecs=audio/pcm; samplerate=16000"
TICKS_PER_SECOND = 10_000_000


class Assessor(Protocol):
    model: str

    def assess(self, wav: bytes, reference: str) -> Metered[Assessment]: ...


def wav_seconds(wav: bytes) -> float:
    """Length of a 16-bit mono PCM WAV, read from its header (what Azure bills)."""
    if len(wav) < 44 or wav[:4] != b"RIFF":
        return 0.0
    rate, byte_rate = struct.unpack_from("<II", wav, 24)
    return (len(wav) - 44) / byte_rate if rate and byte_rate else 0.0


class FakeAssessor:
    """Every word right unless the clip is silent, so the loop can run offline."""

    model = "fake-stt"

    def assess(self, wav: bytes, reference: str) -> Metered[Assessment]:
        units = {"audio_seconds": wav_seconds(wav)}
        if not any(wav[44:]):
            return Metered(Assessment(False, 0, 0, 0, ()), units)
        words = tuple(WordScore(w.strip(".,!?;:"), 95.0, None, (95.0,)) for w in reference.split())
        return Metered(Assessment(True, 95.0, 95.0, 100.0, words), units)


class AzureAssessor:
    model = "azure-speech-pronunciation"

    def __init__(self, key: str, region: str) -> None:
        self._key = key
        self._url = (
            f"https://{region}.stt.speech.microsoft.com/speech/recognition/"
            "conversation/cognitiveservices/v1"
        )

    def assess(self, wav: bytes, reference: str) -> Metered[Assessment]:
        config = {
            "ReferenceText": reference,
            "GradingSystem": "HundredMark",
            "Granularity": "Phoneme",
            "Dimension": "Comprehensive",
            "EnableMiscue": True,
        }
        try:
            response = httpx.post(
                self._url,
                # fr-FR caught more vowel errors than fr-CA in testing; prosody is English-only.
                params={"language": "fr-FR", "format": "detailed"},
                content=wav,
                headers={
                    "Ocp-Apim-Subscription-Key": self._key,
                    "Content-Type": WAV_MIME,
                    "Pronunciation-Assessment": base64.b64encode(
                        json.dumps(config).encode()
                    ).decode(),
                },
                timeout=30,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(f"Azure pronunciation assessment failed: {exc}") from exc
        body = response.json()
        seconds = body.get("Duration", 0) / TICKS_PER_SECOND or wav_seconds(wav)
        return Metered(parse(body), {"audio_seconds": seconds})


def parse(body: dict[str, Any]) -> Assessment:
    best = (body.get("NBest") or [None])[0]
    if body.get("RecognitionStatus") != "Success" or best is None:
        return Assessment(False, 0, 0, 0, ())
    scores = _scores(best)
    words = tuple(_word(w) for w in best.get("Words", []))
    return Assessment(
        recognised=bool(words),
        accuracy=float(scores.get("AccuracyScore", 0)),
        fluency=float(scores.get("FluencyScore", 0)),
        completeness=float(scores.get("CompletenessScore", 0)),
        words=words,
    )


def _word(entry: dict[str, Any]) -> WordScore:
    scores = _scores(entry)
    error = scores.get("ErrorType")
    return WordScore(
        word=entry["Word"],
        accuracy=float(scores.get("AccuracyScore", 0)),
        error=None if error in (None, "None") else error,
        sounds=tuple(float(_scores(p).get("AccuracyScore", 0)) for p in entry.get("Phonemes", [])),
    )


def _scores(entry: dict[str, Any]) -> dict[str, Any]:
    # The detailed format nests scores under PronunciationAssessment; older shapes are flat.
    nested: dict[str, Any] = entry.get("PronunciationAssessment", entry)
    return nested
