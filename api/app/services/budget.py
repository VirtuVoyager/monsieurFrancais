from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from functools import lru_cache

from sqlalchemy import ScalarResult, func, select, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.calendar import MonthWindow, month_window
from app.domain.cost import PriceBook, Units, load_price_book
from app.models import Budget, BudgetReservation, UsageEvent

SERVICES = ("openai", "speech")
TOTAL = "total"


class BudgetExceededError(Exception):
    def __init__(self, cap_name: str, cap: Decimal, projected: Decimal) -> None:
        super().__init__(f"{cap_name} budget of ${cap} would be exceeded (${projected:.4f})")
        self.cap_name = cap_name
        self.cap = cap
        self.projected = projected


@dataclass(frozen=True)
class MonthTotals:
    window: MonthWindow
    caps: dict[str, Decimal]
    spent: dict[str, Decimal]
    reserved: dict[str, Decimal]


@lru_cache
def price_book() -> PriceBook:
    return load_price_book(get_settings().content_dir / "pricing.yaml")


def current_window(now: datetime | None = None) -> MonthWindow:
    return month_window(now or datetime.now(UTC), get_settings().timezone)


def caps_for(session: Session, user_id: int, month: str) -> dict[str, Decimal]:
    """Caps carry forward: a month without its own rows uses the latest earlier month's caps."""
    settings = get_settings()
    caps = {
        "openai": Decimal(str(settings.default_cap_openai_usd)),
        "speech": Decimal(str(settings.default_cap_speech_usd)),
        TOTAL: Decimal(str(settings.default_cap_total_usd)),
    }
    latest_month = session.scalar(
        select(func.max(Budget.month)).where(Budget.user_id == user_id, Budget.month <= month)
    )
    if latest_month:
        rows = session.scalars(
            select(Budget).where(Budget.user_id == user_id, Budget.month == latest_month)
        )
        caps.update({row.service: row.cap_usd for row in rows})
    return caps


def set_caps(session: Session, user_id: int, month: str, caps: dict[str, Decimal]) -> None:
    for service, cap in caps.items():
        row = session.scalar(
            select(Budget).where(
                Budget.user_id == user_id, Budget.month == month, Budget.service == service
            )
        )
        if row is None:
            session.add(Budget(user_id=user_id, month=month, service=service, cap_usd=cap))
        else:
            row.cap_usd = cap
    session.commit()


def month_totals(session: Session, user_id: int, window: MonthWindow) -> MonthTotals:
    spent_rows = session.execute(
        select(UsageEvent.service, func.sum(UsageEvent.cost_usd))
        .where(
            UsageEvent.user_id == user_id,
            UsageEvent.occurred_at >= window.start,
            UsageEvent.occurred_at < window.end,
        )
        .group_by(UsageEvent.service)
    )
    reserved_rows = session.execute(
        select(BudgetReservation.service, func.sum(BudgetReservation.estimated_usd))
        .where(BudgetReservation.user_id == user_id, BudgetReservation.settled_at.is_(None))
        .group_by(BudgetReservation.service)
    )
    return MonthTotals(
        window=window,
        caps=caps_for(session, user_id, window.key),
        spent=_with_total(dict(spent_rows.all())),
        reserved=_with_total(dict(reserved_rows.all())),
    )


def free_used(session: Session, user_id: int, model: str, window: MonthWindow) -> Units:
    rows: ScalarResult[dict[str, float]] = session.scalars(
        select(UsageEvent.free_units).where(
            UsageEvent.user_id == user_id,
            UsageEvent.model == model,
            UsageEvent.occurred_at >= window.start,
            UsageEvent.occurred_at < window.end,
        )
    )
    used: defaultdict[str, float] = defaultdict(float)
    for free_units in rows:
        for unit, amount in free_units.items():
            used[unit] += amount
    return dict(used)


def reserve(
    session: Session, user_id: int, service: str, feature: str, estimate_usd: Decimal
) -> BudgetReservation:
    # Serialises concurrent reservations for this learner until the transaction commits.
    session.execute(text("select pg_advisory_xact_lock(:key)"), {"key": user_id})
    totals = month_totals(session, user_id, current_window())
    for cap_name in (service, TOTAL):
        projected = totals.spent[cap_name] + totals.reserved[cap_name] + estimate_usd
        if projected > totals.caps[cap_name]:
            raise BudgetExceededError(cap_name, totals.caps[cap_name], projected)
    reservation = BudgetReservation(
        user_id=user_id, service=service, feature=feature, estimated_usd=estimate_usd
    )
    session.add(reservation)
    session.commit()
    return reservation


def settle(session: Session, reservation: BudgetReservation, event: UsageEvent | None) -> None:
    reservation.settled_at = datetime.now(UTC)
    reservation.usage_event_id = event.id if event else None
    session.commit()


def _with_total(by_service: dict[str, Decimal]) -> dict[str, Decimal]:
    totals = {service: Decimal(by_service.get(service) or 0) for service in SERVICES}
    totals[TOTAL] = sum(totals.values(), start=Decimal(0))
    return totals
