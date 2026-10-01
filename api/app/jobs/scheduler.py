from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

import structlog
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.services import knowledge, notes, speaking, writing
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


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Background work lives in the API process until it needs its own worker."""
    scheduler = BackgroundScheduler()
    if get_settings().jobs_enabled:
        scheduler.add_job(_run("embed_pending", _embed), "interval", minutes=1)
        scheduler.add_job(_run("close_speaking", speaking.close_expired), "interval", minutes=1)
        scheduler.add_job(_run("grade_speaking", speaking.grade_pending), "interval", minutes=10)
        scheduler.add_job(_run("extract_notes", notes.extract_pending), "interval", minutes=10)
        scheduler.add_job(_run("grade_pending", writing.grade_pending), "interval", minutes=10)
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)
