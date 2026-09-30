from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.coverage import CHECK_PASS_MARK
from app.domain.exercises import CheckResult, check
from app.errors import ForbiddenError, NotFoundError
from app.models import AssessmentRun, Item, Module, Response
from app.schemas.learning import ItemAnswer
from app.services.path import module_progress, open_module

KIND = "module_check"


@dataclass(frozen=True)
class CheckGrade:
    module_id: str
    score: float
    results: list[tuple[str, CheckResult]]

    @property
    def passed(self) -> bool:
        return self.score >= CHECK_PASS_MARK


def start(session: Session, user_id: int, module_id: str) -> tuple[AssessmentRun, list[Item]]:
    module, view = open_module(session, user_id, module_id)
    if len(view.lessons_done(module_id)) < len(module.lessons):
        raise ForbiddenError("Finish every lesson before the module check")
    items = live_items(session, module_id)
    run = AssessmentRun(user_id=user_id, kind=KIND, scope_id=module_id)
    session.add(run)
    session.commit()
    return run, items


def submit(session: Session, user_id: int, run_id: int, answers: list[ItemAnswer]) -> CheckGrade:
    run = session.get(AssessmentRun, run_id)
    if run is None or run.user_id != user_id or run.kind != KIND or run.scope_id is None:
        raise NotFoundError("Module check not found")
    if run.finished_at is not None:
        raise ForbiddenError("This module check was already submitted")

    items = {item.id: item for item in live_items(session, run.scope_id)}
    by_item = {answer.item_id: answer for answer in answers}
    results: list[tuple[str, CheckResult]] = []
    for item_id, item in items.items():
        answer = by_item.get(item_id)
        result = check(
            {"kind": item.kind, **item.payload, **item.answer}, answer.response if answer else {}
        )
        results.append((item_id, result))
        session.add(
            Response(
                run_id=run.id,
                item_id=item_id,
                skill=item.skill,
                answer=answer.response if answer else {},
                correct=result.correct,
                time_ms=answer.time_ms if answer else None,
            )
        )

    score = sum(r.correct for _, r in results) / len(results) if results else 0.0
    run.score = score
    run.finished_at = datetime.now(UTC)
    progress = module_progress(session, user_id, run.scope_id)
    progress.check_score = max(progress.check_score or 0.0, score)
    session.commit()
    _mark_covered_if_done(session, user_id, run.scope_id)
    return CheckGrade(run.scope_id, score, results)


def live_items(session: Session, module_id: str) -> list[Item]:
    return list(
        session.scalars(
            select(Item)
            .where(Item.module_id == module_id, Item.status == "live")
            .order_by(Item.key)
        )
    )


def _mark_covered_if_done(session: Session, user_id: int, module_id: str) -> None:
    progress = module_progress(session, user_id, module_id)
    module = session.get(Module, module_id)
    assert module is not None
    if (
        progress.covered_at is None
        and (progress.check_score or 0) >= CHECK_PASS_MARK
        and len(progress.lessons_done) >= len(module.lessons)
    ):
        progress.covered_at = datetime.now(UTC)
        session.commit()
