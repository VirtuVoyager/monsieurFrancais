from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.speaking import examiner_instructions, usage_units, worst_case_units
from app.llm import get_realtime
from app.llm.realtime import FakeRealtime
from app.models import AssessmentRun, BudgetReservation, UsageEvent
from app.services import budget, speaking

OFFER = {"sdp": "v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n"}
PRICED = "gpt-realtime-2.1-mini"
USAGE: dict[str, Any] = {
    "total_tokens": 1450,
    "input_tokens": 1200,
    "output_tokens": 250,
    "input_token_details": {
        "text_tokens": 900,
        "audio_tokens": 300,
        "cached_tokens": 800,
        "cached_tokens_details": {"text_tokens": 700, "audio_tokens": 100},
    },
    "output_token_details": {"text_tokens": 50, "audio_tokens": 200},
}


@pytest.fixture
def realtime() -> FakeRealtime:
    fake = get_realtime()
    assert isinstance(fake, FakeRealtime)
    fake.hung_up.clear()
    return fake


def _connected(client: TestClient, task: str = "EO1") -> int:
    run_id: int = client.post("/speaking/sessions", json={"task": task}).json()["run_id"]
    assert client.post(f"/speaking/sessions/{run_id}/call", json=OFFER).status_code == 200
    return run_id


def test_usage_splits_cached_tokens_out_of_fresh_input() -> None:
    assert usage_units(USAGE) == {
        "text_input_tokens": 200.0,
        "cached_text_input_tokens": 700.0,
        "audio_input_tokens": 200.0,
        "cached_audio_input_tokens": 100.0,
        "text_output_tokens": 50.0,
        "audio_output_tokens": 200.0,
    }
    assert usage_units({}) == {}


def test_worst_case_grows_faster_than_the_clock() -> None:
    short, long = worst_case_units(120), worst_case_units(270)

    assert long["audio_input_tokens"] > 2 * short["audio_input_tokens"]
    assert budget.price_book().for_model(PRICED).cost(long) < 2


def test_examiner_keeps_private_notes_and_stays_in_french() -> None:
    text = examiner_instructions("EO2", "Posez-moi des questions.", "Rent 850 $.")

    assert "Exercice en interaction" in text
    assert "Private notes, never read out: Rent 850 $." in text
    assert "only French" in text


def test_tasks_follow_the_exam_timings(client: TestClient) -> None:
    tasks = {t["code"]: t for t in client.get("/speaking/tasks").json()}

    assert set(tasks) == {"EO1", "EO2", "EO3"}
    assert tasks["EO2"]["prep_seconds"] == 120
    assert sum(t["prep_seconds"] + t["seconds"] for t in tasks.values()) == 12 * 60


def test_a_session_shows_the_prompt_but_not_the_examiner_notes(
    client: TestClient, seeded: Session
) -> None:
    body = client.post("/speaking/sessions", json={"task": "EO2"}).json()

    assert body["task"]["code"] == "EO2"
    assert "Posez-moi des questions" in body["prompt"]
    assert "850" not in str(body)


def test_connecting_holds_the_worst_case_and_ending_releases_it(
    client: TestClient, seeded: Session, realtime: FakeRealtime
) -> None:
    run_id = _connected(client)

    held = seeded.scalars(select(BudgetReservation).where(BudgetReservation.settled_at.is_(None)))
    assert [r.feature for r in held] == ["speaking"]
    transcript = [{"role": "examiner", "text": "Bonjour, présentez-vous."}]
    assert (
        client.post(f"/speaking/sessions/{run_id}/end", json={"transcript": transcript}).status_code
        == 204
    )

    run = seeded.get_one(AssessmentRun, run_id)
    assert run.finished_at is not None
    assert run.result["transcript"] == transcript
    assert realtime.hung_up == [run.result["call_id"]]
    assert (
        seeded.scalars(
            select(BudgetReservation).where(BudgetReservation.settled_at.is_(None))
        ).all()
        == []
    )


def test_each_response_is_metered_and_the_call_stops_at_the_reservation(
    client: TestClient,
    seeded: Session,
    realtime: FakeRealtime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(realtime, "model", PRICED)
    run_id = _connected(client)
    usage_url = f"/speaking/sessions/{run_id}/usage"

    assert client.post(usage_url, json={"usage": USAGE}).json() == {"stop": False}
    event = seeded.scalars(select(UsageEvent)).one()
    assert (event.feature, event.model, event.cost_usd > 0) == ("speaking", PRICED, True)

    runaway = {"input_token_details": {"audio_tokens": 100_000}}
    assert client.post(usage_url, json={"usage": runaway}).json() == {"stop": True}
    assert len(realtime.hung_up) == 1
    assert seeded.get_one(AssessmentRun, run_id).finished_at is not None


def test_a_session_cannot_start_over_the_cap(
    client: TestClient, seeded: Session, realtime: FakeRealtime, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(realtime, "model", PRICED)
    client.put("/budget/caps", json={"openai": 0.05, "speech": 1, "total": 1})
    run_id = client.post("/speaking/sessions", json={"task": "EO3"}).json()["run_id"]

    assert client.post(f"/speaking/sessions/{run_id}/call", json=OFFER).status_code == 402


def test_a_session_connects_only_once(client: TestClient, seeded: Session) -> None:
    run_id = _connected(client)

    assert client.post(f"/speaking/sessions/{run_id}/call", json=OFFER).status_code == 403


def test_abandoned_sessions_are_hung_up_after_the_deadline(
    client: TestClient, seeded: Session, realtime: FakeRealtime
) -> None:
    run_id = _connected(client)
    assert speaking.close_expired(seeded) == 0

    run = seeded.get_one(AssessmentRun, run_id)
    past = datetime.now(UTC) - timedelta(minutes=5)
    run.result = {**run.result, "deadline": past.isoformat()}
    seeded.commit()

    assert speaking.close_expired(seeded) == 1
    assert realtime.hung_up == [run.result["call_id"]]
    assert client.post(f"/speaking/sessions/{run_id}/usage", json={"usage": USAGE}).json() == {
        "stop": True
    }
