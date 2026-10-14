from collections.abc import Callable
from decimal import Decimal

import structlog
from sqlalchemy.orm import Session

from app.domain.cost import Metered, Units, split_free
from app.models import UsageEvent
from app.services import budget

log = structlog.get_logger()


def run_metered[T](
    session: Session,
    *,
    user_id: int,
    feature: str,
    model: str,
    estimate_usd: Decimal,
    call: Callable[[], Metered[T]],
) -> T:
    """The only way to make a request/response paid call: reserve, call, record, settle."""
    pricing = budget.price_book().for_model(model)
    reservation = budget.reserve(session, user_id, pricing.service, feature, estimate_usd)
    try:
        result = call()
    except Exception:
        budget.settle(session, reservation, None)
        raise

    event = record_usage(session, user_id=user_id, feature=feature, model=model, units=result.units)
    budget.settle(session, reservation, event)
    return result.value


def record_usage(
    session: Session, *, user_id: int, feature: str, model: str, units: Units
) -> UsageEvent:
    """Prices units already consumed; callers must hold a reservation covering them."""
    book = budget.price_book()
    pricing = book.for_model(model)
    used = budget.free_used(session, user_id, model, budget.current_window())
    free_left = {unit: cap - used.get(unit, 0.0) for unit, cap in pricing.free_monthly.items()}
    billable, free = split_free(units, free_left)
    event = UsageEvent(
        user_id=user_id,
        service=pricing.service,
        model=model,
        feature=feature,
        units=units,
        free_units=free,
        cost_usd=pricing.cost(billable),
        price_version=book.version,
        request_id=structlog.contextvars.get_contextvars().get("request_id"),
    )
    session.add(event)
    session.flush()
    log.info("usage_recorded", model=model, feature=feature, cost_usd=str(event.cost_usd))
    return event
