import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.exercises import CheckResult, check
from app.domain.scales import RECEPTIVE
from app.errors import ForbiddenError, NotFoundError
from app.models import AssessmentRun, Item, Response
from app.schemas.learning import ItemAnswer
from app.services.skills import exam_scales, working_ability

KIND = "drill"
GRACE = timedelta(seconds=15)
# Aim slightly above current ability so drills stretch rather than confirm.
STRETCH = 0.5


@dataclass(frozen=True)
class DrillGrade:
    skill: str
    score: float
    results: list[tuple[str, CheckResult]]


def start(
    session: Session, user_id: int, skill: str, count: int
) -> tuple[AssessmentRun, list[Item]]:
    if skill not in RECEPTIVE:
        raise NotFoundError(f"No timed drills for {skill}")
    target = working_ability(session, user_id, skill) + STRETCH
    recent = set(
        session.scalars(
            select(Response.item_id)
            .join(AssessmentRun, AssessmentRun.id == Response.run_id)
            .where(
                AssessmentRun.user_id == user_id,
                AssessmentRun.created_at >= datetime.now(UTC) - timedelta(days=14),
            )
        )
    )
    bank = list(
        session.scalars(
            select(Item).where(Item.skill == skill, Item.status == "live", Item.module_id.is_(None))
        )
    )
    fresh = [item for item in bank if item.id not in recent]
    pool = fresh if len(fresh) >= count else bank
    random.shuffle(pool)
    chosen = sorted(pool, key=lambda item: abs(item.difficulty - target))[:count]
    # TCF sections run from easiest to hardest.
    chosen.sort(key=lambda item: item.difficulty)

    seconds = exam_scales().seconds_per_item[skill] * len(chosen)
    deadline = datetime.now(UTC) + timedelta(seconds=seconds)
    run = AssessmentRun(
        user_id=user_id,
        kind=KIND,
        scope_id=skill,
        result={"item_ids": [item.id for item in chosen], "deadline": deadline.isoformat()},
    )
    session.add(run)
    session.commit()
    return run, chosen


def deadline_of(run: AssessmentRun) -> datetime:
    return datetime.fromisoformat(run.result["deadline"])


def submit(session: Session, user_id: int, run_id: int, answers: list[ItemAnswer]) -> DrillGrade:
    run = session.get(AssessmentRun, run_id)
    if run is None or run.user_id != user_id or run.kind != KIND or run.scope_id is None:
        raise NotFoundError("Drill not found")
    if run.finished_at is not None:
        raise ForbiddenError("This drill was already submitted")

    late = datetime.now(UTC) > deadline_of(run) + GRACE
    by_item = {answer.item_id: answer for answer in answers}
    items = {
        item.id: item
        for item in session.scalars(select(Item).where(Item.id.in_(run.result["item_ids"])))
    }
    results: list[tuple[str, CheckResult]] = []
    for item_id in run.result["item_ids"]:
        item = items[item_id]
        answer = by_item.get(item_id)
        response = answer.response if answer and not late else {}
        result = check({"kind": item.kind, **item.payload, **item.answer}, response)
        results.append((item_id, result))
        session.add(
            Response(
                run_id=run.id,
                item_id=item_id,
                skill=item.skill,
                answer=answer.response if answer else {},
                correct=result.correct,
                time_ms=answer.time_ms if answer else None,
                timed_out=late or answer is None,
            )
        )
    score = sum(r.correct for _, r in results) / len(results) if results else 0.0
    run.score = score
    run.finished_at = datetime.now(UTC)
    session.commit()
    return DrillGrade(run.scope_id, score, results)
