from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
Provider = Literal["fake", "azure"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", env_prefix="MF_", extra="ignore")

    database_url: str = "postgresql+psycopg://mf:mf@localhost:5432/mf"
    content_dir: Path = REPO_ROOT / "content"
    media_dir: Path = REPO_ROOT / "media"
    media_manifest: Path = REPO_ROOT / "content" / "media_manifest.csv"
    timezone: str = "Asia/Kolkata"
    log_level: str = "INFO"
    log_json: bool = True
    otel_endpoint: str | None = None

    # Each capability switches to Azure independently, as its deployment becomes available.
    grader_provider: Provider = "fake"
    notes_provider: Provider = "fake"
    glossary_provider: Provider = "fake"
    embedding_provider: Provider = "fake"
    speech_provider: Provider = "fake"
    realtime_provider: Provider = "fake"
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_text_deployment: str = "gpt-5.4-mini"
    azure_openai_embedding_deployment: str = "text-embedding-3-small"
    azure_openai_realtime_deployment: str = "gpt-realtime-2.1-mini"
    azure_speech_key: str | None = None
    azure_speech_region: str | None = None

    default_cap_openai_usd: float = 5.0
    default_cap_speech_usd: float = 2.0
    default_cap_total_usd: float = 6.0

    jobs_enabled: bool = True
    # The hosted app builds audio and glossaries for new modules itself; locally that stays the
    # explicit `make audio` / `make glossary`, so a dev server never spends on its own.
    content_jobs_enabled: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]
    secret_key: str | None = None
    # When set, the first-run passphrase setup also asks for this code, so whoever finds a
    # freshly deployed URL first cannot claim the account.
    setup_code: str | None = None
    cookie_secure: bool = False
    session_days: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
