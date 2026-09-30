from functools import cache

import openai

from app.config import get_settings
from app.llm.azure import AzureGrader
from app.llm.embedder import AzureEmbedder, Embedder, FakeEmbedder
from app.llm.fake import FakeGrader
from app.llm.grader import Grader
from app.llm.notes import AzureNoteExtractor, FakeNoteExtractor, NoteExtractor
from app.llm.realtime import AzureRealtime, FakeRealtime, Realtime


@cache
def _client() -> openai.OpenAI:
    settings = get_settings()
    if not (settings.azure_openai_endpoint and settings.azure_openai_api_key):
        raise RuntimeError("Azure OpenAI needs MF_AZURE_OPENAI_ENDPOINT and _API_KEY")
    return openai.OpenAI(
        base_url=f"{settings.azure_openai_endpoint.rstrip('/')}/openai/v1/",
        api_key=settings.azure_openai_api_key,
        max_retries=3,
    )


# The only place provider clients are built; every call still goes through run_metered.
@cache
def get_grader() -> Grader:
    settings = get_settings()
    if settings.grader_provider == "fake":
        return FakeGrader()
    return AzureGrader(_client(), settings.azure_openai_text_deployment)


@cache
def get_embedder() -> Embedder:
    settings = get_settings()
    if settings.embedding_provider == "fake":
        return FakeEmbedder()
    return AzureEmbedder(_client(), settings.azure_openai_embedding_deployment)


@cache
def get_note_extractor() -> NoteExtractor:
    settings = get_settings()
    if settings.notes_provider == "fake":
        return FakeNoteExtractor()
    return AzureNoteExtractor(_client(), settings.azure_openai_text_deployment)


@cache
def get_realtime() -> Realtime:
    settings = get_settings()
    if settings.realtime_provider == "fake":
        return FakeRealtime()
    return AzureRealtime(_client(), settings.azure_openai_realtime_deployment)
