import subprocess
import threading
import time
from typing import Protocol

import httpx

from app.domain.audio import AudioRequest
from app.domain.cost import Metered
from app.llm.grader import ProviderUnavailableError

OUTPUT_FORMAT = "ogg-24khz-16bit-mono-opus"


class Synthesizer(Protocol):
    model: str

    def synthesize(self, request: AudioRequest) -> Metered[bytes]: ...


def _billable(request: AudioRequest) -> dict[str, float]:
    # Azure bills the spoken text, not the SSML markup around it.
    return {"characters": float(len(request.text.strip()))}


class FakeSynthesizer:
    """Silent Ogg Opus of a plausible length, so playback paths work without Azure."""

    model = "fake-speech"

    def synthesize(self, request: AudioRequest) -> Metered[bytes]:
        seconds = max(len(request.text) / 15, 0.5)
        audio = subprocess.run(
            [
                "ffmpeg",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=24000:cl=mono",
                "-t",
                f"{seconds:.2f}",
                "-c:a",
                "libopus",
                "-f",
                "ogg",
                "pipe:1",
            ],
            check=True,
            capture_output=True,
        ).stdout
        return Metered(audio, _billable(request))


class AzureSynthesizer:
    model = "azure-speech-tts"
    # The free tier allows 20 requests a minute; stay just under it.
    min_interval = 3.1

    def __init__(self, key: str, region: str) -> None:
        self._client = httpx.Client(
            base_url=f"https://{region}.tts.speech.microsoft.com",
            headers={
                "Ocp-Apim-Subscription-Key": key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": OUTPUT_FORMAT,
                "User-Agent": "monsieur-francais",
            },
            timeout=30,
        )
        self._lock = threading.Lock()
        self._last = 0.0

    def synthesize(self, request: AudioRequest) -> Metered[bytes]:
        with self._lock:
            wait = self._last + self.min_interval - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
        try:
            response = self._client.post("/cognitiveservices/v1", content=request.ssml.encode())
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(f"Azure TTS failed: {exc}") from exc
        return Metered(response.content, _billable(request))
