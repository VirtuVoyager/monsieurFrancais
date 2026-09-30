from fastapi import APIRouter

from app.db import SessionDep
from app.presenters import module_summary
from app.schemas.learning import CheckResultOut, ExerciseAnswer, LessonCompleted, LessonOut
from app.services import lessons, library
from app.services.path import load_path, module_progress, open_module
from app.services.users import CurrentUser

router = APIRouter(prefix="/lessons", tags=["lessons"])


@router.get("/{lesson_id:path}")
def get_lesson(lesson_id: str, session: SessionDep, user: CurrentUser) -> LessonOut:
    lesson = lessons.get_lesson(session, lesson_id)
    _, view = open_module(session, user.id, lesson.module_id)
    return LessonOut(
        id=lesson.id,
        module_id=lesson.module_id,
        title=lesson.title,
        done=lesson.id in view.lessons_done(lesson.module_id),
        content=lessons.content(session, lesson),
    )


@router.post("/{lesson_id:path}/check")
def check_exercise(
    lesson_id: str, answer: ExerciseAnswer, session: SessionDep, user: CurrentUser
) -> CheckResultOut:
    lesson = lessons.get_lesson(session, lesson_id)
    open_module(session, user.id, lesson.module_id)
    result = lessons.check_exercise(lesson, answer.index, answer.response)
    return CheckResultOut(
        correct=result.correct, expected=result.expected, explanation=result.explanation
    )


@router.post("/{lesson_id:path}/complete")
def complete_lesson(lesson_id: str, session: SessionDep, user: CurrentUser) -> LessonCompleted:
    lesson = lessons.get_lesson(session, lesson_id)
    module, _ = open_module(session, user.id, lesson.module_id)
    progress = module_progress(session, user.id, lesson.module_id)
    if lesson.id not in progress.lessons_done:
        progress.lessons_done = [*progress.lessons_done, lesson.id]
    cards_added = library.enroll_lesson(session, user.id, lesson)
    session.commit()
    return LessonCompleted(
        module=module_summary(module, load_path(session, user.id)), cards_added=cards_added
    )
