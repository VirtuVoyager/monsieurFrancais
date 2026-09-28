from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BudgetReservation, UsageEvent
from app.services import budget
from app.services.metering import Metered, run_metered
from app.services.users import get_or_create_learner


def _tts(chars: int) -> Metered[bytes]:
    return Metered(value=b"audio", units={"characters": chars})


def test_paid_call_records_usage_and_settles_reservation(session: Session) -> None:
    user = get_or_create_learner(session)

    result = run_metered(
        session,
        user_id=user.id,
        feature="grading",
        model="gpt-5.4-mini",
        estimate_usd=Decimal("0.01"),
        call=lambda: Metered(value="ok", units={"input_tokens": 1000, "output_tokens": 200}),
    )

    event = session.scalars(select(UsageEvent)).one()
    assert result == "ok"
    assert event.cost_usd == Decimal("0.00165")
    assert session.scalars(select(BudgetReservation)).one().usage_event_id == event.id


def test_speech_free_tier_is_used_before_paying(session: Session) -> None:
    user = get_or_create_learner(session)
    run_it = dict(user_id=user.id, feature="tts", model="azure-speech-tts", estimate_usd=Decimal(0))

    run_metered(session, **run_it, call=lambda: _tts(499_000))  # type: ignore[arg-type]
    run_metered(session, **run_it, call=lambda: _tts(3_000))  # type: ignore[arg-type]

    last = session.scalars(select(UsageEvent).order_by(UsageEvent.id.desc())).first()
    assert last is not None
    assert last.free_units == {"characters": 1000}
    assert last.cost_usd == Decimal("0.032")


def test_call_is_refused_when_cap_would_be_exceeded(session: Session) -> None:
    user = get_or_create_learner(session)
    budget.set_caps(
        session,
        user.id,
        budget.current_window().key,
        {"openai": Decimal("0.05"), "speech": Decimal(1), "total": Decimal(1)},
    )
    called = False

    def call() -> Metered[str]:
        nonlocal called
        called = True
        return Metered(value="x", units={})

    with pytest.raises(budget.BudgetExceededError) as exc:
        run_metered(
            session,
            user_id=user.id,
            feature="grading",
            model="gpt-5.4-mini",
            estimate_usd=Decimal("0.06"),
            call=call,
        )

    assert exc.value.cap_name == "openai"
    assert not called


def test_failed_call_releases_its_reservation(session: Session) -> None:
    user = get_or_create_learner(session)

    def boom() -> Metered[str]:
        raise RuntimeError("azure down")

    with pytest.raises(RuntimeError):
        run_metered(
            session,
            user_id=user.id,
            feature="grading",
            model="gpt-5.4-mini",
            estimate_usd=Decimal("0.02"),
            call=boom,
        )

    totals = budget.month_totals(session, user.id, budget.current_window())
    assert totals.reserved["openai"] == 0
    assert session.scalars(select(UsageEvent)).first() is None


def test_open_reservations_count_against_the_cap(session: Session) -> None:
    user = get_or_create_learner(session)
    budget.set_caps(
        session,
        user.id,
        budget.current_window().key,
        {"openai": Decimal(1), "speech": Decimal(1), "total": Decimal("0.30")},
    )
    budget.reserve(session, user.id, "openai", "examiner", Decimal("0.25"))

    with pytest.raises(budget.BudgetExceededError) as exc:
        budget.reserve(session, user.id, "speech", "tts", Decimal("0.10"))

    assert exc.value.cap_name == "total"


def test_caps_carry_forward_to_later_months(session: Session) -> None:
    user = get_or_create_learner(session)
    budget.set_caps(
        session,
        user.id,
        "2026-01",
        {"openai": Decimal(3), "speech": Decimal(1), "total": Decimal(4)},
    )

    assert budget.caps_for(session, user.id, "2026-05")["openai"] == Decimal(3)
    assert budget.caps_for(session, user.id, "2025-12")["openai"] == Decimal("5.0")
