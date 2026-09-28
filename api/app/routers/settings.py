from dataclasses import asdict
from datetime import date

from fastapi import APIRouter

from app.db import SessionDep
from app.domain.planning import exam_plan
from app.schemas.settings import ExamPlanOut, LearnerSettings, SettingsOut
from app.services.users import CurrentUser

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def get_settings(user: CurrentUser) -> SettingsOut:
    return _out(LearnerSettings.model_validate(user.settings))


@router.put("")
def update_settings(body: LearnerSettings, session: SessionDep, user: CurrentUser) -> SettingsOut:
    user.settings = body.model_dump(mode="json")
    session.commit()
    return _out(body)


def _out(settings: LearnerSettings) -> SettingsOut:
    plan = exam_plan(settings.exam_date, date.today()) if settings.exam_date else None
    return SettingsOut(
        settings=settings, plan=ExamPlanOut.model_validate(asdict(plan)) if plan else None
    )
