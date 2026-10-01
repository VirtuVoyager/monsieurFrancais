from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.domain.cost import Metered
from app.domain.rubric import (
    Rubric,
    RubricPass,
    TaggedError,
    combine,
    needs_another_pass,
    word_count,
)
from app.llm import get_grader
from app.llm.grader import Grader, ProviderUnavailableError, WritingTask
from app.models import ErrorTag, WritingSubmission
from app.services import knowledge
from app.services.budget import BudgetExceededError, price_book
from app.services.metering import run_metered

log = structlog.get_logger()
EXPECTED_OUTPUT_TOKENS = 1500
PROMPT_TOKENS = 1500


def submit(
    session: Session,
    user_id: int,
    task: WritingTask,
    text: str,
    *,
    lesson_id: str | None = None,
    run_id: int | None = None,
    item_id: str | None = None,
) -> WritingSubmission:
    """Saves the text first so nothing is lost, then grades it if budget and provider allow."""
    submission = WritingSubmission(
        user_id=user_id,
        run_id=run_id,
        lesson_id=lesson_id,
        item_id=item_id,
        task=task.code,
        prompt=task.prompt,
        text=text,
        word_count=word_count(text),
        status="pending",
    )
    session.add(submission)
    session.commit()
    try_grade(session, submission, task)
    return submission


def try_grade(
    session: Session, submission: WritingSubmission, task: WritingTask, grader: Grader | None = None
) -> bool:
    return grade_with(session, submission, lambda g: g.grade_writing(task, submission.text), grader)


def grade_with(
    session: Session,
    submission: WritingSubmission,
    one_pass: Callable[[Grader], Metered[RubricPass]],
    grader: Grader | None = None,
) -> bool:
    """Grades a saved text with any rubric; a budget cap or outage leaves it pending for later."""
    grader = grader or get_grader()
    try:
        rubric = _grade(session, submission, lambda: one_pass(grader), grader.model)
    except (BudgetExceededError, ProviderUnavailableError) as exc:
        log.warning("grading_deferred", submission_id=submission.id, reason=str(exc))
        return False
    submission.rubric = _serialize(rubric)
    submission.score = rubric.score
    submission.status = "graded"
    submission.graded_at = datetime.now(UTC)
    _record_errors(session, submission.user_id, rubric.errors)
    knowledge.index_user(session, submission.user_id)
    session.commit()
    return True


def top_errors(session: Session, user_id: int, limit: int = 5) -> list[ErrorTag]:
    return list(
        session.scalars(
            select(ErrorTag)
            .where(ErrorTag.user_id == user_id)
            .order_by(ErrorTag.count.desc(), ErrorTag.last_seen.desc())
            .limit(limit)
        )
    )


def _grade(
    session: Session,
    submission: WritingSubmission,
    call: Callable[[], Metered[RubricPass]],
    model: str,
) -> Rubric:
    estimate = _estimate_usd(model, submission.text)

    def one_pass() -> RubricPass:
        return run_metered(
            session,
            user_id=submission.user_id,
            feature="grading",
            model=model,
            estimate_usd=estimate,
            call=call,
        )

    passes = [one_pass(), one_pass()]
    if needs_another_pass(passes):
        passes.append(one_pass())
    return combine(passes)


def _estimate_usd(model: str, text: str) -> Decimal:
    tokens = {
        "input_tokens": PROMPT_TOKENS + len(text) / 3,
        "output_tokens": EXPECTED_OUTPUT_TOKENS,
    }
    return price_book().for_model(model).cost(tokens)


def _record_errors(session: Session, user_id: int, errors: list[TaggedError]) -> None:
    now = datetime.now(UTC)
    for error in errors:
        session.execute(
            insert(ErrorTag)
            .values(
                user_id=user_id,
                tag=error.tag,
                example=error.excerpt,
                correction=error.correction,
                count=1,
                last_seen=now,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "tag"],
                set_={
                    "count": ErrorTag.count + 1,
                    "example": error.excerpt,
                    "correction": error.correction,
                    "last_seen": now,
                },
            )
        )


def _serialize(rubric: Rubric) -> dict[str, object]:
    return {
        "criteria": rubric.criteria,
        "evidence": rubric.evidence,
        "fixes": [asdict(f) for f in rubric.fixes],
        "errors": [asdict(e) for e in rubric.errors],
        "passes": rubric.passes,
    }
