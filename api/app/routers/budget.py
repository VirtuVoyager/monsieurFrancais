from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter
from sqlalchemy import func, select

from app.db import SessionDep
from app.models import UsageEvent
from app.schemas.budget import (
    BudgetSummary,
    CapsUpdate,
    FeatureSpend,
    FreeAllowance,
    ServiceSpend,
    UsageEventOut,
)
from app.services import budget
from app.services.users import CurrentUser

router = APIRouter(prefix="/budget", tags=["budget"])


@router.get("")
def get_summary(session: SessionDep, user: CurrentUser) -> BudgetSummary:
    window = budget.current_window()
    totals = budget.month_totals(session, user.id, window)
    elapsed = max(window.fraction_elapsed(datetime.now(UTC)), 1 / 31)
    services = {
        name: ServiceSpend(
            cap_usd=totals.caps[name],
            spent_usd=totals.spent[name],
            reserved_usd=totals.reserved[name],
            projected_usd=(totals.spent[name] / Decimal(str(elapsed))).quantize(Decimal("0.0001")),
        )
        for name in (*budget.SERVICES, budget.TOTAL)
    }
    by_feature = session.execute(
        select(UsageEvent.feature, func.sum(UsageEvent.cost_usd))
        .where(
            UsageEvent.user_id == user.id,
            UsageEvent.occurred_at >= window.start,
            UsageEvent.occurred_at < window.end,
        )
        .group_by(UsageEvent.feature)
        .order_by(func.sum(UsageEvent.cost_usd).desc())
    )
    book = budget.price_book()
    free: list[FreeAllowance] = []
    for model, pricing in book.models.items():
        used = budget.free_used(session, user.id, model, window) if pricing.free_monthly else {}
        free += [
            FreeAllowance(model=model, unit=unit, allowance=allowance, used=used.get(unit, 0.0))
            for unit, allowance in pricing.free_monthly.items()
        ]
    return BudgetSummary(
        month=window.key,
        price_version=book.version,
        services=services,
        by_feature=[FeatureSpend(feature=f, cost_usd=c) for f, c in by_feature],
        free_allowances=free,
    )


@router.put("/caps", status_code=204)
def update_caps(caps: CapsUpdate, session: SessionDep, user: CurrentUser) -> None:
    budget.set_caps(session, user.id, budget.current_window().key, caps.model_dump())


@router.get("/events")
def list_events(
    session: SessionDep, user: CurrentUser, limit: int = 50, feature: str | None = None
) -> list[UsageEventOut]:
    query = select(UsageEvent).where(UsageEvent.user_id == user.id)
    if feature:
        query = query.where(UsageEvent.feature == feature)
    events = session.scalars(query.order_by(UsageEvent.occurred_at.desc()).limit(min(limit, 500)))
    return [UsageEventOut.model_validate(e, from_attributes=True) for e in events]
