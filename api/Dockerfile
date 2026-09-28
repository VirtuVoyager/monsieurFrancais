FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
WORKDIR /app/api

COPY api/pyproject.toml api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY api/ ./
COPY content/ /app/content/
ENV PATH="/app/api/.venv/bin:$PATH" MF_CONTENT_DIR=/app/content MF_MEDIA_DIR=/app/media

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python -m app.jobs.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
