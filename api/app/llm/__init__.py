from functools import cache

import openai

from app.config import get_settings
from app.llm.azure import AzureGrader
from app.llm.fake import FakeGrader
from app.llm.grader import Grader


@cache
def get_grader() -> Grader:
    """The only place provider clients are built; every call still goes through run_metered."""
    settings = get_settings()
    if settings.providers == "fake":
        return FakeGrader()
    if not (settings.azure_openai_endpoint and settings.azure_openai_api_key):
        raise RuntimeError("MF_PROVIDERS=azure needs MF_AZURE_OPENAI_ENDPOINT and _API_KEY")
    client = openai.OpenAI(
        base_url=f"{settings.azure_openai_endpoint.rstrip('/')}/openai/v1/",
        api_key=settings.azure_openai_api_key,
        max_retries=3,
    )
    return AzureGrader(client, settings.azure_openai_text_deployment)
