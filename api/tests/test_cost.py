from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.config import get_settings
from app.domain.calendar import month_window
from app.domain.cost import ModelPricing, Rate, load_price_book, split_free

TTS = ModelPricing(
    service="speech",
    rates={"characters": Rate(usd=Decimal("16"), per=1_000_000)},
    free_monthly={"characters": 500_000},
)


def test_cost_is_rate_times_units() -> None:
    assert TTS.cost({"characters": 250_000}) == Decimal("4")


def test_unknown_unit_is_rejected() -> None:
    with pytest.raises(ValueError, match="audio_seconds"):
        TTS.cost({"audio_seconds": 10})


def test_free_allowance_is_consumed_before_billing() -> None:
    billable, free = split_free({"characters": 300}, {"characters": 100})

    assert billable == {"characters": 200}
    assert free == {"characters": 100}


def test_exhausted_allowance_bills_everything() -> None:
    billable, free = split_free({"characters": 300}, {"characters": -5})

    assert billable == {"characters": 300}
    assert free == {}


def test_repo_price_book_loads_every_model() -> None:
    book = load_price_book(get_settings().content_dir / "pricing.yaml")

    assert book.for_model("gpt-5.4-mini").service == "openai"
    assert book.for_model("azure-speech-tts").free_monthly == {"characters": 500_000}


def test_month_window_uses_learner_timezone() -> None:
    # 20:00 UTC on 31 Jan is already 1 Feb in Kolkata.
    window = month_window(datetime(2026, 1, 31, 20, 0, tzinfo=UTC), "Asia/Kolkata")

    assert window.key == "2026-02"
    assert window.end.month == 3
