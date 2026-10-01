from functools import cache

from app.config import get_settings
from app.speech.synthesizer import AzureSynthesizer, FakeSynthesizer, Synthesizer
from app.speech.transcriber import AzureTranscriber, FakeTranscriber, Transcriber


# The only place Speech clients are built; every call still goes through run_metered.
@cache
def get_synthesizer() -> Synthesizer:
    if get_settings().speech_provider == "fake":
        return FakeSynthesizer()
    return AzureSynthesizer(*_credentials())


@cache
def get_transcriber() -> Transcriber:
    if get_settings().speech_provider == "fake":
        return FakeTranscriber()
    return AzureTranscriber(*_credentials())


def _credentials() -> tuple[str, str]:
    settings = get_settings()
    if not (settings.azure_speech_key and settings.azure_speech_region):
        raise RuntimeError("Azure Speech needs MF_AZURE_SPEECH_KEY and MF_AZURE_SPEECH_REGION")
    return settings.azure_speech_key, settings.azure_speech_region
