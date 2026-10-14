from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.rubric import word_count
from app.domain.speaking import (
    GRACE_SECONDS,
    PACES,
    Turn,
    as_text,
    examiner_instructions,
    interleave,
    usage_units,
    worst_case_units,
)
from app.errors import ForbiddenError, NotFoundError
from app.llm import get_realtime
from app.llm.grader import ProviderUnavailableError, SpokenTask
from app.models import AssessmentRun, BudgetReservation, Item, WritingSubmission
from app.services import budget, grading, metering
from app.services.budget import BudgetExceededError
from app.services.skills import exam_scales
from app.speech import get_transcriber

log = structlog.get_logger()
EXTENSIONS = {"audio/webm": ".webm", "audio/ogg": ".ogg", "audio/mp4": ".m4a", "audio/wav": ".wav"}

KIND = "speaking"
SKILL = "EO"
FEATURE = "speaking"


def start(
    session: Session, user_id: int, task: str, pace: str, show_transcript: bool
) -> tuple[AssessmentRun, Item]:
    if task not in exam_scales().speaking_tasks:
        raise NotFoundError(f"No speaking task {task}")
    if pace not in PACES:
        raise NotFoundError(f"No pace {pace}")
    last_used = (
        select(func.max(AssessmentRun.created_at))
        .where(
            AssessmentRun.user_id == user_id,
            AssessmentRun.kind == KIND,
            AssessmentRun.result["item_id"].astext == Item.id,
        )
        .scalar_subquery()
    )
    item = session.scalar(
        select(Item)
        .where(Item.skill == SKILL, Item.status == "live", Item.payload["task"].astext == task)
        .order_by(last_used.asc().nulls_first(), Item.id)
        .limit(1)
    )
    if item is None:
        raise NotFoundError(f"No {task} prompts in the bank")
    # Only the real test's conditions may move the speaking bar.
    exam = pace == "exam" and not show_transcript
    run = AssessmentRun(
        user_id=user_id,
        kind=KIND,
        scope_id=SKILL,
        result={"item_id": item.id, "task": task, "pace": pace, "exam": exam},
    )
    session.add(run)
    session.commit()
    return run, item


def connect(session: Session, user_id: int, run_id: int, offer_sdp: str) -> tuple[str, datetime]:
    """Holds the session's worst-case cost against the cap before the examiner can speak."""
    run = _run(session, user_id, run_id)
    if "call_id" in run.result or run.finished_at:
        raise ForbiddenError("This speaking session has already started")
    item = session.get_one(Item, run.result["item_id"])
    seconds = exam_scales().speaking_tasks[run.result["task"]].seconds
    realtime = get_realtime()
    pricing = budget.price_book().for_model(realtime.model)
    estimate = pricing.cost(worst_case_units(seconds))
    reservation = budget.reserve(session, user_id, pricing.service, FEATURE, estimate)
    pace = run.result["pace"]
    instructions = examiner_instructions(
        run.result["task"], item.payload["prompt"], item.answer.get("examiner"), pace
    )
    try:
        call = realtime.connect(offer_sdp, instructions, PACES[pace])
    except Exception:
        budget.settle(session, reservation, None)
        raise
    deadline = datetime.now(UTC) + timedelta(seconds=seconds)
    run.result = {
        **run.result,
        "call_id": call.call_id,
        "model": realtime.model,
        "reservation_id": reservation.id,
        "deadline": deadline.isoformat(),
        "cost_usd": "0",
    }
    session.commit()
    return call.answer_sdp, deadline


def record(session: Session, user_id: int, run_id: int, usage: Mapping[str, Any]) -> bool:
    """Meters one examiner response; True means the session must stop now."""
    run = _run(session, user_id, run_id, lock=True)
    if run.finished_at or "call_id" not in run.result:
        return True
    cost = Decimal(run.result["cost_usd"])
    units = usage_units(usage)
    if units:
        event = metering.record_usage(
            session, user_id=user_id, feature=FEATURE, model=run.result["model"], units=units
        )
        cost += event.cost_usd
        run.result = {**run.result, "cost_usd": str(cost)}
    held = session.get_one(BudgetReservation, run.result["reservation_id"]).estimated_usd
    stop = (held > 0 and cost >= held) or _expired(run, datetime.now(UTC))
    if stop:
        _close(session, run)
    session.commit()
    return stop


def save_recording(session: Session, user_id: int, run_id: int, audio: bytes, mime: str) -> None:
    """Keeps the learner's own voice, to transcribe for grading and to play back later."""
    run = _run(session, user_id, run_id, lock=True)
    if "call_id" not in run.result:
        raise ForbiddenError("Nothing was recorded: the session never connected")
    relative = f"users/{user_id}/speaking/{run.id}{EXTENSIONS.get(mime, '.bin')}"
    path = get_settings().media_dir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(audio)
    run.result = {**run.result, "recording": {"path": relative, "mime": mime}}
    session.commit()


def end(
    session: Session, user_id: int, run_id: int, transcript: list[dict[str, Any]]
) -> WritingSubmission | None:
    """Hangs up, then grades the learner's side if the examiner was ever reached."""
    run = _run(session, user_id, run_id, lock=True)
    run.result = {**run.result, "transcript": transcript}
    if not run.finished_at:
        _close(session, run)
    session.commit()
    if "call_id" not in run.result:
        return None
    existing = submission_of(session, run)
    if existing:
        return existing
    item = session.get_one(Item, run.result["item_id"])
    submission = WritingSubmission(
        user_id=user_id,
        run_id=run.id,
        item_id=item.id,
        skill=SKILL,
        task=run.result["task"],
        prompt=item.payload["prompt"],
        text="",
        word_count=0,
    )
    session.add(submission)
    session.commit()
    try_grade(session, submission)
    return submission


def try_grade(session: Session, submission: WritingSubmission) -> bool:
    run = session.get_one(AssessmentRun, submission.run_id)
    if not submission.text and not _transcribe(session, run, submission):
        return False
    if submission.status == "empty":
        return True
    seconds = exam_scales().speaking_tasks[submission.task].seconds
    task = SpokenTask(submission.task, submission.prompt, seconds)
    return grading.grade_with(
        session, submission, lambda grader: grader.grade_speaking(task, submission.text)
    )


def grade_pending(session: Session) -> int:
    """Retries answers deferred by a budget cap or an unavailable provider."""
    pending = session.scalars(
        select(WritingSubmission).where(
            WritingSubmission.status == "pending", WritingSubmission.skill == SKILL
        )
    ).all()
    return sum(try_grade(session, submission) for submission in pending)


def result(
    session: Session, user_id: int, run_id: int
) -> tuple[AssessmentRun, WritingSubmission | None]:
    run = _run(session, user_id, run_id)
    return run, submission_of(session, run)


def recording(session: Session, user_id: int, run_id: int) -> tuple[Path, str]:
    run = _run(session, user_id, run_id)
    saved = run.result.get("recording")
    if not saved:
        raise NotFoundError("No recording for this session")
    return get_settings().media_dir / saved["path"], saved["mime"]


def submission_of(session: Session, run: AssessmentRun) -> WritingSubmission | None:
    return session.scalar(select(WritingSubmission).where(WritingSubmission.run_id == run.id))


def close_expired(session: Session) -> int:
    """Hangs up sessions the browser abandoned, so they stop billing and release the cap."""
    now = datetime.now(UTC)
    open_runs = session.scalars(
        select(AssessmentRun).where(
            AssessmentRun.kind == KIND,
            AssessmentRun.finished_at.is_(None),
            AssessmentRun.result.has_key("call_id"),
        )
    )
    expired = [run for run in open_runs if _expired(run, now)]
    for run in expired:
        _close(session, run)
    session.commit()
    return len(expired)


def _run(session: Session, user_id: int, run_id: int, *, lock: bool = False) -> AssessmentRun:
    query = select(AssessmentRun).where(AssessmentRun.id == run_id, AssessmentRun.kind == KIND)
    run = session.scalar(query.with_for_update() if lock else query)
    if run is None or run.user_id != user_id:
        raise NotFoundError("Speaking session not found")
    return run


def _expired(run: AssessmentRun, now: datetime) -> bool:
    deadline = datetime.fromisoformat(run.result["deadline"])
    return now > deadline + timedelta(seconds=GRACE_SECONDS)


def _transcribe(session: Session, run: AssessmentRun, submission: WritingSubmission) -> bool:
    saved = run.result.get("recording")
    if not saved:
        submission.status = "empty"
        session.commit()
        return True
    transcriber = get_transcriber()
    audio = (get_settings().media_dir / saved["path"]).read_bytes()
    seconds = exam_scales().speaking_tasks[submission.task].seconds + GRACE_SECONDS
    pricing = budget.price_book().for_model(transcriber.model)
    try:
        heard = metering.run_metered(
            session,
            user_id=submission.user_id,
            feature="transcription",
            model=transcriber.model,
            estimate_usd=pricing.cost({"audio_seconds": float(seconds)}),
            call=lambda: transcriber.transcribe(audio, saved["mime"]),
        )
    except (BudgetExceededError, ProviderUnavailableError) as exc:
        log.warning("transcription_deferred", submission_id=submission.id, reason=str(exc))
        return False
    examiner = [
        Turn("examiner", line["text"], int(line.get("at_ms", 0)))
        for line in run.result.get("transcript", [])
        if line.get("role") == "examiner"
    ]
    candidate = [Turn("candidate", p.text, p.offset_ms) for p in heard.phrases if p.text.strip()]
    if not candidate:
        submission.status = "empty"
    submission.text = as_text(interleave(examiner, candidate))
    submission.word_count = word_count(" ".join(t.text for t in candidate))
    session.commit()
    return True


def _close(session: Session, run: AssessmentRun) -> None:
    run.finished_at = datetime.now(UTC)
    if "call_id" in run.result:
        get_realtime().hangup(run.result["call_id"])
        reservation = session.get_one(BudgetReservation, run.result["reservation_id"])
        budget.settle(session, reservation, None)
