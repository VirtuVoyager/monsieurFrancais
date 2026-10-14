import json
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.domain.cost import Metered
from app.llm.grader import ProviderUnavailableError

# Fast transcription handles a whole speaking task (up to two hours) in one synchronous call.
API_VERSION = "2024-11-15"


@dataclass(frozen=True)
class Phrase:
    offset_ms: int
    text: str


@dataclass(frozen=True)
class Transcript:
    phrases: list[Phrase]
    duration_ms: int


class Transcriber(Protocol):
    model: str

    def transcribe(self, audio: bytes, mime: str) -> Metered[Transcript]: ...


class FakeTranscriber:
    """A fixed beginner answer, with typical errors, so grading has something to mark."""

    model = "fake-stt"

    def transcribe(self, audio: bytes, mime: str) -> Metered[Transcript]:
        phrases = [
            Phrase(2_000, "Bonjour, je suis Alex et je suis trente ans."),
            Phrase(9_000, "Je habite à Montréal avec ma famille. Je suis un ingénieur."),
        ]
        return Metered(Transcript(phrases, 15_000), {"audio_seconds": 15.0})


class AzureTranscriber:
    model = "azure-speech-stt"

    def __init__(self, key: str, region: str) -> None:
        self._key = key
        self._url = (
            f"https://{region}.api.cognitive.microsoft.com/speechtotext/"
            f"transcriptions:transcribe?api-version={API_VERSION}"
        )

    def transcribe(self, audio: bytes, mime: str) -> Metered[Transcript]:
        try:
            response = httpx.post(
                self._url,
                headers={"Ocp-Apim-Subscription-Key": self._key},
                files={"audio": ("answer", audio, mime)},
                # Both accents the TCF accepts; the service picks per phrase.
                data={"definition": json.dumps({"locales": ["fr-FR", "fr-CA"]})},
                timeout=120,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(f"Azure transcription failed: {exc}") from exc
        body = response.json()
        phrases = [Phrase(int(p["offsetMilliseconds"]), p["text"]) for p in body.get("phrases", [])]
        duration_ms = int(body.get("durationMilliseconds", 0))
        return Metered(Transcript(phrases, duration_ms), {"audio_seconds": duration_ms / 1000})
