from fastapi import APIRouter

from app.db import SessionDep
from app.presenters import writing_result
from app.routers.skills import level_out
from app.schemas.learning import (
    ErrorFingerprintOut,
    WritingDrillOut,
    WritingResult,
    WritingText,
)
from app.services import grading, lessons, skills, writing
from app.services.path import open_module
from app.services.users import CurrentUser

router = APIRouter(tags=["writing"])


@router.post("/lessons/{lesson_id:path}/writing")
def submit_lesson_writing(
    lesson_id: str, body: WritingText, session: SessionDep, user: CurrentUser
) -> WritingResult:
    lesson = lessons.get_lesson(session, lesson_id)
    open_module(session, user.id, lesson.module_id)
    return writing_result(writing.submit_lesson(session, user.id, lesson, body.text))


@router.post("/writing/drills")
def start_writing_drill(session: SessionDep, user: CurrentUser) -> WritingDrillOut:
    run, item = writing.start_drill(session, user.id)
    task = writing.task_for_item(item)
    return WritingDrillOut(
        run_id=run.id,
        task=task.code,
        prompt=task.prompt,
        min_words=task.min_words,
        max_words=task.max_words,
        deadline=run.result["deadline"],
    )


@router.post("/writing/drills/{run_id}")
def submit_writing_drill(
    run_id: int, body: WritingText, session: SessionDep, user: CurrentUser
) -> WritingResult:
    submission = writing.submit_drill(session, user.id, run_id, body.text)
    result = writing_result(submission)
    result.level = level_out(skills.skill_level(session, user.id, "EE"))
    return result


@router.get("/errors")
def error_fingerprint(session: SessionDep, user: CurrentUser) -> list[ErrorFingerprintOut]:
    return [
        ErrorFingerprintOut(tag=e.tag, count=e.count, example=e.example, correction=e.correction)
        for e in grading.top_errors(session, user.id)
    ]
