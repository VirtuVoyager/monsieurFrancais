from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

import structlog
from sqlalchemy.orm import Session

from app.domain.cost import Units, split_free
from app.models import UsageEvent
from app.services import budget

log = structlog.get_logger()


@dataclass(frozen=True)
class Metered[T]:
    value: T
    units: Units


def run_metered[T](
    session: Session,
    *,
    user_id: int,
    feature: str,
    model: str,
    estimate_usd: Decimal,
    call: Callable[[], Metered[T]],
) -> T:
    """The only way to make a paid call: reserve against the cap, call, record, settle."""
    book = budget.price_book()
    pricing = book.for_model(model)
    reservation = budget.reserve(session, user_id, pricing.service, feature, estimate_usd)
    try:
        result = call()
    except Exception:
        budget.settle(session, reservation, None)
        raise

    window = budget.current_window()
    used = budget.free_used(session, user_id, model, window)
    free_left = {unit: cap - used.get(unit, 0.0) for unit, cap in pricing.free_monthly.items()}
    billable, free = split_free(result.units, free_left)
    event = UsageEvent(
        user_id=user_id,
        service=pricing.service,
        model=model,
        feature=feature,
        units=result.units,
        free_units=free,
        cost_usd=pricing.cost(billable),
        price_version=book.version,
        request_id=structlog.contextvars.get_contextvars().get("request_id"),
    )
    session.add(event)
    session.flush()
    budget.settle(session, reservation, event)
    log.info("usage_recorded", model=model, feature=feature, cost_usd=str(event.cost_usd))
    return result.value
