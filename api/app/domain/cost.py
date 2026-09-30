from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

Units = dict[str, float]


@dataclass(frozen=True)
class Metered[T]:
    """A provider result plus the billable units it consumed."""

    value: T
    units: Units


@dataclass(frozen=True)
class Rate:
    usd: Decimal
    per: int


@dataclass(frozen=True)
class ModelPricing:
    service: str
    rates: dict[str, Rate]
    free_monthly: dict[str, float] = field(default_factory=dict)

    def cost(self, units: Units) -> Decimal:
        unknown = units.keys() - self.rates.keys()
        if unknown:
            raise ValueError(f"No rate for units: {sorted(unknown)}")
        total = Decimal(0)
        for name, amount in units.items():
            rate = self.rates[name]
            total += Decimal(str(amount)) * rate.usd / rate.per
        return total


@dataclass(frozen=True)
class PriceBook:
    version: str
    models: dict[str, ModelPricing]

    def for_model(self, model: str) -> ModelPricing:
        try:
            return self.models[model]
        except KeyError:
            raise ValueError(f"Model {model!r} is missing from pricing.yaml") from None


def split_free(units: Units, free_left: Units) -> tuple[Units, Units]:
    """Returns (billable, free): free allowance is consumed before anything is billed."""
    billable: Units = {}
    free: Units = {}
    for name, amount in units.items():
        covered = min(amount, max(free_left.get(name, 0.0), 0.0))
        if covered:
            free[name] = covered
        if amount - covered:
            billable[name] = amount - covered
    return billable, free


def load_price_book(path: Path) -> PriceBook:
    raw: dict[str, Any] = yaml.safe_load(path.read_text())
    models = {
        name: ModelPricing(
            service=spec["service"],
            rates={
                unit: Rate(usd=Decimal(str(r["usd"])), per=int(r["per"]))
                for unit, r in spec["rates"].items()
            },
            free_monthly={k: float(v) for k, v in spec.get("free_monthly", {}).items()},
        )
        for name, spec in raw["models"].items()
    }
    return PriceBook(version=str(raw["version"]), models=models)
