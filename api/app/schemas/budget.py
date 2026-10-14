from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ServiceSpend(BaseModel):
    cap_usd: Decimal
    spent_usd: Decimal
    reserved_usd: Decimal
    projected_usd: Decimal


class FeatureSpend(BaseModel):
    feature: str
    cost_usd: Decimal


class FreeAllowance(BaseModel):
    model: str
    unit: str
    allowance: float
    used: float


class BudgetSummary(BaseModel):
    month: str
    price_version: str
    services: dict[str, ServiceSpend]
    by_feature: list[FeatureSpend]
    free_allowances: list[FreeAllowance]


class CapsUpdate(BaseModel):
    openai: Decimal = Field(ge=0)
    speech: Decimal = Field(ge=0)
    total: Decimal = Field(ge=0)


class UsageEventOut(BaseModel):
    occurred_at: datetime
    service: str
    model: str
    feature: str
    units: dict[str, float]
    free_units: dict[str, float]
    cost_usd: Decimal
