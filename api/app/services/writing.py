from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import ForbiddenError, NotFoundError
from app.llm.grader import WritingTask
from app.models import AssessmentRun, Item, Lesson, WritingSubmission
from app.services import grading
from app.services.skills import exam_scales, working_ability

KIND = "drill"
SKILL = "EE"
GRACE = timedelta(seconds=30)
# Writing task by ability (logits): EE1 below B1, EE2 at B1, the argumentative EE3 from B2.
TASK_THRESHOLDS = ((0.0, "EE3"), (-1.0, "EE2"))


def task_for_item(item: Item) -> WritingTask:
    spec = exam_scales().writing_tasks[item.payload["task"]]
    return WritingTask(item.payload["task"], item.payload["prompt"], spec.min_words, spec.max_words)


def task_for_lesson(lesson: Lesson) -> WritingTask:
    p = lesson.payload
    return WritingTask(p["task"], p["prompt"].strip(), p["min_words"], p["max_words"])


def submit_lesson(session: Session, user_id: int, lesson: Lesson, text: str) -> WritingSubmission:
    if lesson.kind != "writing":
        raise NotFoundError("Not a writing lesson")
    return grading.submit(session, user_id, task_for_lesson(lesson), text, lesson_id=lesson.id)


def start_drill(session: Session, user_id: int) -> tuple[AssessmentRun, Item]:
    ability = working_ability(session, user_id, SKILL)
    task = next((t for threshold, t in TASK_THRESHOLDS if ability >= threshold), "EE1")
    last_used = (
        select(func.max(WritingSubmission.created_at))
        .where(WritingSubmission.item_id == Item.id, WritingSubmission.user_id == user_id)
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
    minutes = exam_scales().writing_tasks[task].minutes
    deadline = datetime.now(UTC) + timedelta(minutes=minutes)
    run = AssessmentRun(
        user_id=user_id,
        kind=KIND,
        scope_id=SKILL,
        result={"item_id": item.id, "deadline": deadline.isoformat()},
    )
    session.add(run)
    session.commit()
    return run, item


def submit_drill(session: Session, user_id: int, run_id: int, text: str) -> WritingSubmission:
    run = session.get(AssessmentRun, run_id)
    if run is None or run.user_id != user_id or run.kind != KIND or run.scope_id != SKILL:
        raise NotFoundError("Writing drill not found")
    if run.finished_at is not None:
        raise ForbiddenError("This writing drill was already submitted")
    item = session.get_one(Item, run.result["item_id"])
    late = datetime.now(UTC) > datetime.fromisoformat(run.result["deadline"]) + GRACE
    run.finished_at = datetime.now(UTC)
    run.result = {**run.result, "late": late}
    session.commit()
    return grading.submit(
        session, user_id, task_for_item(item), text, run_id=run.id, item_id=item.id
    )


def grade_pending(session: Session) -> int:
    """Retries submissions deferred by a budget cap or an unavailable grader."""
    pending = session.scalars(
        select(WritingSubmission).where(WritingSubmission.status == "pending")
    ).all()
    graded = 0
    for submission in pending:
        if submission.lesson_id:
            task = task_for_lesson(session.get_one(Lesson, submission.lesson_id))
        elif submission.item_id:
            task = task_for_item(session.get_one(Item, submission.item_id))
        else:
            continue
        graded += grading.try_grade(session, submission, task)
    return graded
