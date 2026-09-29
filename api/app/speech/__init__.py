from functools import cache

from app.config import get_settings
from app.speech.synthesizer import AzureSynthesizer, FakeSynthesizer, Synthesizer


# The only place the Speech client is built; every call still goes through run_metered.
@cache
def get_synthesizer() -> Synthesizer:
    settings = get_settings()
    if settings.speech_provider == "fake":
        return FakeSynthesizer()
    if not (settings.azure_speech_key and settings.azure_speech_region):
        raise RuntimeError("Azure Speech needs MF_AZURE_SPEECH_KEY and MF_AZURE_SPEECH_REGION")
    return AzureSynthesizer(settings.azure_speech_key, settings.azure_speech_region)
