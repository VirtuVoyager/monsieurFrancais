from dataclasses import dataclass
from datetime import date, timedelta

# Test centres fill 6-8 weeks ahead; TCF Canada requires 30 days between sittings.
BOOK_AHEAD = timedelta(weeks=8)
RETAKE_GAP = timedelta(days=30)
FINAL_PHASE = timedelta(weeks=4)
MOCK_EVERY_BUILD = 30
MOCK_EVERY_FINAL = 7


@dataclass(frozen=True)
class ExamPlan:
    exam_date: date
    days_left: int
    book_by: date
    earliest_retake: date
    final_phase: bool
    mock_every_days: int
    booking_overdue: bool


def exam_plan(exam_date: date, today: date) -> ExamPlan:
    final_phase = exam_date - today <= FINAL_PHASE
    return ExamPlan(
        exam_date=exam_date,
        days_left=(exam_date - today).days,
        book_by=exam_date - BOOK_AHEAD,
        earliest_retake=exam_date + RETAKE_GAP,
        final_phase=final_phase,
        mock_every_days=MOCK_EVERY_FINAL if final_phase else MOCK_EVERY_BUILD,
        booking_overdue=today > exam_date - BOOK_AHEAD and today <= exam_date,
    )
