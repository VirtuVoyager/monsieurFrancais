from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, CreatedAt

Money = Numeric(12, 6)


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    service: Mapped[str] = mapped_column(String(10))
    model: Mapped[str] = mapped_column(String(60))
    feature: Mapped[str] = mapped_column(String(30))
    units: Mapped[dict[str, Any]]
    free_units: Mapped[dict[str, Any]] = mapped_column(default=dict)
    cost_usd: Mapped[Decimal] = mapped_column(Money)
    price_version: Mapped[str] = mapped_column(String(20))
    request_id: Mapped[str | None] = mapped_column(String(64))


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (UniqueConstraint("user_id", "month", "service"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    month: Mapped[str] = mapped_column(String(7))
    service: Mapped[str] = mapped_column(String(10))
    cap_usd: Mapped[Decimal] = mapped_column(Money)


class BudgetReservation(CreatedAt, Base):
    __tablename__ = "budget_reservations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    service: Mapped[str] = mapped_column(String(10))
    feature: Mapped[str] = mapped_column(String(30))
    estimated_usd: Mapped[Decimal] = mapped_column(Money)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    usage_event_id: Mapped[int | None] = mapped_column(ForeignKey("usage_events.id"))
