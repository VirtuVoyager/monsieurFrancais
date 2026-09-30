from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.speaking import GRACE_SECONDS, examiner_instructions, usage_units, worst_case_units
from app.errors import ForbiddenError, NotFoundError
from app.llm import get_realtime
from app.models import AssessmentRun, BudgetReservation, Item
from app.services import budget, metering
from app.services.skills import exam_scales

KIND = "speaking"
SKILL = "EO"
FEATURE = "speaking"


def start(session: Session, user_id: int, task: str) -> tuple[AssessmentRun, Item]:
    if task not in exam_scales().speaking_tasks:
        raise NotFoundError(f"No speaking task {task}")
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
    run = AssessmentRun(
        user_id=user_id, kind=KIND, scope_id=SKILL, result={"item_id": item.id, "task": task}
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
    instructions = examiner_instructions(
        run.result["task"], item.payload["prompt"], item.answer.get("examiner")
    )
    try:
        call = realtime.connect(offer_sdp, instructions)
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


def end(session: Session, user_id: int, run_id: int, transcript: list[dict[str, str]]) -> None:
    run = _run(session, user_id, run_id, lock=True)
    run.result = {**run.result, "transcript": transcript}
    if not run.finished_at:
        _close(session, run)
    session.commit()


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


def _close(session: Session, run: AssessmentRun) -> None:
    run.finished_at = datetime.now(UTC)
    if "call_id" in run.result:
        get_realtime().hangup(run.result["call_id"])
        reservation = session.get_one(BudgetReservation, run.result["reservation_id"])
        budget.settle(session, reservation, None)
