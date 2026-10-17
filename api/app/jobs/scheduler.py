from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import structlog
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.services import audio, glossary, knowledge, notes, speaking, writing
from app.services.users import get_or_create_learner

log = structlog.get_logger()


def _run(name: str, job: Callable[[Session], int]) -> Callable[[], None]:
    def run() -> None:
        try:
            with SessionLocal() as session:
                count = job(session)
            if count:
                log.info("job_done", job=name, count=count)
        except Exception:
            log.exception("job_failed", job=name)

    return run


def _embed(session: Session) -> int:
    return knowledge.embed_pending(session, get_or_create_learner(session).id)


def _note_audio(session: Session) -> int:
    return audio.generate_notes(session).generated


def _catalogue_audio(session: Session) -> int:
    return audio.generate_missing(session, get_or_create_learner(session).id).generated


def _glossaries(session: Session) -> int:
    return len(glossary.build_modules(session, get_or_create_learner(session).id).built)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Background work lives in the API process until it needs its own worker."""
    scheduler = BackgroundScheduler()
    settings = get_settings()
    if settings.jobs_enabled:
        scheduler.add_job(_run("embed_pending", _embed), "interval", minutes=1)
        scheduler.add_job(_run("close_speaking", speaking.close_expired), "interval", minutes=1)
        scheduler.add_job(_run("grade_speaking", speaking.grade_pending), "interval", minutes=10)
        scheduler.add_job(_run("extract_notes", notes.extract_pending), "interval", minutes=10)
        scheduler.add_job(_run("note_audio", _note_audio), "interval", minutes=5)
        scheduler.add_job(_run("grade_pending", writing.grade_pending), "interval", minutes=10)
    if settings.jobs_enabled and settings.content_jobs_enabled:
        # Modules arrive with a deploy; each clip and glossary is paid once (hash-cached), so a
        # check shortly after every start costs nothing when nothing changed.
        soon = datetime.now(UTC) + timedelta(minutes=2)
        for name, job in (("catalogue_audio", _catalogue_audio), ("glossaries", _glossaries)):
            scheduler.add_job(_run(name, job), "interval", hours=6, next_run_time=soon)
    if scheduler.get_jobs():
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)
