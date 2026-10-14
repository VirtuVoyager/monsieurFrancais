from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Item


def _answer_all(session: Session, run: dict[str, Any], right: bool) -> list[dict[str, Any]]:
    answers = []
    for entry in run["items"]:
        item = session.get_one(Item, entry["id"])
        choice = item.answer["answer"] if right else (item.answer["answer"] + 1) % 3
        answers.append({"item_id": item.id, "response": {"choice": choice}})
    return answers


def test_placement_covers_both_sections_across_all_levels(
    client: TestClient, seeded: Session
) -> None:
    run = client.post("/placement").json()

    items = [seeded.get_one(Item, e["id"]) for e in run["items"]]
    skills = [i.skill for i in items]
    assert skills == ["CO"] * 8 + ["CE"] * 8
    assert {i.cefr for i in items} == {"A1", "A2", "B1", "B2"}


def test_strong_placement_places_lower_modules(client: TestClient, seeded: Session) -> None:
    run = client.post("/placement").json()

    outcome = client.post(
        f"/placement/{run['run_id']}", json={"answers": _answer_all(seeded, run, right=True)}
    ).json()

    path = client.get("/path").json()
    assert outcome["placed_level"] != "A1"
    assert outcome["modules_placed"] == 2
    assert outcome["levels"]["CO"] and outcome["levels"]["CE"]
    assert [m["status"] for m in path["levels"][0]["modules"]] == ["placed", "placed"]
    assert path["coverage"]["covered"] == 2


def test_weak_placement_starts_at_a1_and_places_nothing(
    client: TestClient, seeded: Session
) -> None:
    run = client.post("/placement").json()

    outcome = client.post(
        f"/placement/{run['run_id']}", json={"answers": _answer_all(seeded, run, right=False)}
    ).json()

    assert outcome["placed_level"] == "A1"
    assert outcome["modules_placed"] == 0
    assert client.get("/skills").json()["CO"]["cefr"] == "A1"


def test_placement_run_cannot_be_submitted_as_a_drill(client: TestClient, seeded: Session) -> None:
    run = client.post("/placement").json()

    assert client.post(f"/drills/{run['run_id']}", json={"answers": []}).status_code == 404
