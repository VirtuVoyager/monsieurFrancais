from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain.cost import Metered
from app.services.metering import run_metered
from app.services.users import get_or_create_learner


def test_summary_reports_spend_by_service_and_feature(client: TestClient, session: Session) -> None:
    user = get_or_create_learner(session)
    run_metered(
        session,
        user_id=user.id,
        feature="grading",
        model="gpt-5.4-mini",
        estimate_usd=Decimal("0.01"),
        call=lambda: Metered(value=None, units={"output_tokens": 1_000_000}),
    )

    body = client.get("/budget").json()

    assert Decimal(body["services"]["openai"]["spent_usd"]) == Decimal("4.5")
    assert Decimal(body["services"]["total"]["spent_usd"]) == Decimal("4.5")
    assert body["by_feature"][0]["feature"] == "grading"
    assert {a["model"] for a in body["free_allowances"]} == {"azure-speech-stt", "azure-speech-tts"}


def test_caps_can_be_updated_and_enforced(client: TestClient) -> None:
    assert (
        client.put("/budget/caps", json={"openai": 2, "speech": 1, "total": 2.5}).status_code == 204
    )

    services = client.get("/budget").json()["services"]

    assert Decimal(services["openai"]["cap_usd"]) == 2
    assert Decimal(services["total"]["cap_usd"]) == Decimal("2.5")


def test_negative_caps_are_rejected(client: TestClient) -> None:
    response = client.put("/budget/caps", json={"openai": -1, "speech": 1, "total": 1})

    assert response.status_code == 422
