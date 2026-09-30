from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AssessmentRun, Item


def _answers(session: Session, drill: dict[str, Any], right: bool) -> list[dict[str, Any]]:
    answers = []
    for entry in drill["items"]:
        item = session.get_one(Item, entry["id"])
        choice = item.answer["answer"] if right else (item.answer["answer"] + 1) % 3
        answers.append({"item_id": item.id, "response": {"choice": choice}})
    return answers


def test_drill_serves_bank_items_easiest_first_with_a_deadline(
    client: TestClient, seeded: Session
) -> None:
    drill = client.post("/drills", json={"skill": "CO", "count": 6}).json()

    items = [seeded.get_one(Item, entry["id"]) for entry in drill["items"]]
    assert len(items) == 6
    assert all(i.module_id is None and i.skill == "CO" for i in items)
    assert [i.difficulty for i in items] == sorted(i.difficulty for i in items)
    assert drill["items"][0]["exercise"]["audio_text"]
    assert "answer" not in drill["items"][0]["exercise"]
    deadline = datetime.fromisoformat(drill["deadline"])
    assert timedelta(seconds=300) < deadline - datetime.now(UTC) <= timedelta(seconds=324)


def test_skills_are_empty_until_timed_evidence_exists(client: TestClient, seeded: Session) -> None:
    assert client.get("/skills").json() == {"CO": None, "CE": None, "EE": None, "EO": None}


def test_submitting_a_drill_produces_a_listening_estimate(
    client: TestClient, seeded: Session
) -> None:
    drill = client.post("/drills", json={"skill": "CO", "count": 6}).json()

    outcome = client.post(
        f"/drills/{drill['run_id']}", json={"answers": _answers(seeded, drill, right=True)}
    ).json()

    level = client.get("/skills").json()["CO"]
    assert outcome["score"] == 1
    assert outcome["level"] == level
    assert level["evidence_count"] == 6
    assert level["cefr"] in {"A2", "B1", "B2", "C1", "C2"}
    assert client.get("/skills").json()["CE"] is None


def test_better_answers_give_a_higher_estimate(client: TestClient, seeded: Session) -> None:
    weak = client.post("/drills", json={"skill": "CE", "count": 6}).json()
    weak_level = client.post(
        f"/drills/{weak['run_id']}", json={"answers": _answers(seeded, weak, right=False)}
    ).json()["level"]
    strong = client.post("/drills", json={"skill": "CE", "count": 6}).json()
    strong_level = client.post(
        f"/drills/{strong['run_id']}", json={"answers": _answers(seeded, strong, right=True)}
    ).json()["level"]

    assert strong_level["score"] > weak_level["score"]


def test_late_submission_counts_every_answer_wrong(client: TestClient, seeded: Session) -> None:
    drill = client.post("/drills", json={"skill": "CO", "count": 3}).json()
    run = seeded.get_one(AssessmentRun, drill["run_id"])
    run.result = {**run.result, "deadline": (datetime.now(UTC) - timedelta(minutes=5)).isoformat()}
    seeded.commit()

    outcome = client.post(
        f"/drills/{drill['run_id']}", json={"answers": _answers(seeded, drill, right=True)}
    ).json()

    assert outcome["score"] == 0


def test_module_checks_never_feed_skill_estimates(client: TestClient, seeded: Session) -> None:
    for lesson in client.get("/modules/a1-01-se-presenter").json()["lessons"]:
        client.post(f"/lessons/{lesson['id']}/complete")
    run = client.post("/modules/a1-01-se-presenter/check").json()
    ce_items = seeded.scalars(
        select(Item).where(Item.module_id == "a1-01-se-presenter", Item.skill == "CE")
    ).all()
    answers = [{"item_id": i.id, "response": {"choice": i.answer["answer"]}} for i in ce_items]
    client.post(f"/checks/{run['run_id']}", json={"answers": answers})

    assert client.get("/skills").json()["CE"] is None


def test_drills_are_only_for_listening_and_reading(client: TestClient, seeded: Session) -> None:
    assert client.post("/drills", json={"skill": "EE"}).status_code == 422
