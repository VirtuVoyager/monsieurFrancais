from itertools import groupby

from fastapi import APIRouter

from app.db import SessionDep
from app.domain.exercises import public
from app.presenters import module_detail, module_summary
from app.schemas.learning import (
    CheckItemOut,
    CheckOutcome,
    CheckSubmission,
    CoverageOut,
    ExerciseOut,
    ItemResult,
    LevelOut,
    ModuleCheckOut,
    ModuleDetail,
    NextLesson,
    PathOut,
)
from app.services import checks
from app.services.path import load_path, open_module
from app.services.users import CurrentUser

router = APIRouter(tags=["path"])


@router.get("/path")
def get_path(session: SessionDep, user: CurrentUser) -> PathOut:
    view = load_path(session, user.id)
    levels = []
    for level, modules in groupby(view.modules, key=lambda m: m.level_id):
        covered, total = view.coverage.by_level[level]
        levels.append(
            LevelOut(
                id=level,
                covered=covered,
                total=total,
                modules=[module_summary(m, view) for m in modules],
            )
        )
    lesson = view.next_lesson()
    module = next((m for m in view.modules if lesson and m.id == lesson.module_id), None)
    return PathOut(
        coverage=CoverageOut(
            covered=view.coverage.covered, total=view.coverage.total, percent=view.coverage.percent
        ),
        levels=levels,
        next_lesson=NextLesson(
            module_id=module.id,
            module_title=module.title,
            lesson_id=lesson.id,
            lesson_title=lesson.title,
        )
        if lesson and module
        else None,
    )


@router.get("/modules/{module_id}")
def get_module(module_id: str, session: SessionDep, user: CurrentUser) -> ModuleDetail:
    module, view = open_module(session, user.id, module_id)
    return module_detail(module, view)


@router.post("/modules/{module_id}/check")
def start_check(module_id: str, session: SessionDep, user: CurrentUser) -> ModuleCheckOut:
    run, items = checks.start(session, user.id, module_id)
    return ModuleCheckOut(
        run_id=run.id,
        items=[
            CheckItemOut(
                id=item.id,
                skill=item.skill,
                exercise=ExerciseOut.model_validate(public({"kind": item.kind, **item.payload})),
            )
            for item in items
        ],
    )


@router.post("/checks/{run_id}")
def submit_check(
    run_id: int, submission: CheckSubmission, session: SessionDep, user: CurrentUser
) -> CheckOutcome:
    grade = checks.submit(session, user.id, run_id, submission.answers)
    view = load_path(session, user.id)
    module = next(m for m in view.modules if m.id == grade.module_id)
    return CheckOutcome(
        score=grade.score,
        passed=grade.passed,
        results=[
            ItemResult(
                item_id=item_id, correct=r.correct, expected=r.expected, explanation=r.explanation
            )
            for item_id, r in grade.results
        ],
        module=module_summary(module, view),
    )
