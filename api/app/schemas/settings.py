from datetime import date
from zoneinfo import available_timezones

from pydantic import BaseModel, Field, field_validator


class LearnerSettings(BaseModel):
    exam_date: date | None = None
    target_nclc: int = Field(default=7, ge=5, le=10)
    daily_minutes: int = Field(default=90, ge=15, le=600)
    timezone: str = "Asia/Kolkata"

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value: str) -> str:
        if value not in available_timezones():
            raise ValueError(f"Unknown timezone {value}")
        return value


class ExamPlanOut(BaseModel):
    exam_date: date
    days_left: int
    book_by: date
    earliest_retake: date
    final_phase: bool
    mock_every_days: int
    booking_overdue: bool


class SettingsOut(BaseModel):
    settings: LearnerSettings
    plan: ExamPlanOut | None
