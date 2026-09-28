from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Item

M1 = "a1-01-se-presenter"
M2 = "a1-02-la-famille"


def _complete_all_lessons(client: TestClient, module_id: str) -> dict[str, Any]:
    body: dict[str, Any] = {}
    for lesson in client.get(f"/modules/{module_id}").json()["lessons"]:
        body = client.post(f"/lessons/{lesson['id']}/complete").json()
    return body


def _correct_answers(session: Session, module_id: str) -> list[dict[str, Any]]:
    answers = []
    for item in session.scalars(select(Item).where(Item.module_id == module_id)):
        if item.kind == "mcq":
            response: dict[str, Any] = {"choice": item.answer["answer"]}
        elif item.kind == "cloze":
            response = {"text": item.answer["accepted"][0]}
        else:
            response = {"text": item.answer["answer"]}
        answers.append({"item_id": item.id, "response": response})
    return answers


def test_new_learner_sees_first_module_open_and_next_locked(
    client: TestClient, seeded: Session
) -> None:
    path = client.get("/path").json()

    modules = path["levels"][0]["modules"]
    assert [m["status"] for m in modules] == ["open", "locked"]
    assert path["next_lesson"]["lesson_id"] == f"{M1}/grammaire"
    assert path["coverage"] == {"covered": 0, "total": 2, "percent": 0.0}


def test_locked_module_cannot_be_opened(client: TestClient, seeded: Session) -> None:
    assert client.get(f"/modules/{M2}").status_code == 403
    assert client.get(f"/lessons/{M2}/grammaire").status_code == 403


def test_lesson_content_hides_answers_and_checks_server_side(
    client: TestClient, seeded: Session
) -> None:
    lesson = client.get(f"/lessons/{M1}/grammaire").json()
    first = lesson["content"]["exercises"][0]

    assert lesson["content"]["kind"] == "grammar"
    assert "accepted" not in first and "answer" not in first
    right = client.post(
        f"/lessons/{M1}/grammaire/check", json={"index": 0, "response": {"text": "suis"}}
    )
    wrong = client.post(
        f"/lessons/{M1}/grammaire/check", json={"index": 0, "response": {"text": "es"}}
    )
    assert right.json()["correct"] is True
    assert wrong.json() == {"correct": False, "expected": "suis", "explanation": None}


def test_module_check_requires_all_lessons(client: TestClient, seeded: Session) -> None:
    assert client.post(f"/modules/{M1}/check").status_code == 403


def test_passing_the_check_covers_the_module_and_unlocks_the_next(
    client: TestClient, seeded: Session
) -> None:
    completed = _complete_all_lessons(client, M1)
    run = client.post(f"/modules/{M1}/check").json()
    outcome = client.post(
        f"/checks/{run['run_id']}", json={"answers": _correct_answers(seeded, M1)}
    ).json()

    path = client.get("/path").json()
    assert completed["module"]["lessons_done"] == 7
    assert outcome["passed"] is True
    assert outcome["module"]["status"] == "covered"
    assert [m["status"] for m in path["levels"][0]["modules"]] == ["covered", "open"]
    assert path["coverage"]["covered"] == 1


def test_failing_the_check_keeps_the_module_open(client: TestClient, seeded: Session) -> None:
    _complete_all_lessons(client, M1)
    run = client.post(f"/modules/{M1}/check").json()

    outcome = client.post(f"/checks/{run['run_id']}", json={"answers": []}).json()

    assert outcome["score"] == 0
    assert outcome["module"]["status"] == "open"
    assert all(r["expected"] for r in outcome["results"])
    assert client.post(f"/checks/{run['run_id']}", json={"answers": []}).status_code == 403


def test_vocab_lesson_fills_library_and_review_queue(client: TestClient, seeded: Session) -> None:
    added = client.post(f"/lessons/{M1}/vocabulaire/complete").json()["cards_added"]
    due = client.get("/reviews/due?limit=50").json()
    reviewed = client.post(f"/reviews/{due[0]['id']}", json={"rating": 3}).json()

    assert added == 20
    assert len(due) == 20
    assert due[0]["prompt_en"] and due[0]["answer_fr"]
    assert reviewed["reviews"] == 1
    assert reviewed["due_at"] > due[0]["due_at"]
    assert {w["lemma"] for w in client.get("/library/words?q=city").json()} == {"ville"}
    assert client.post(f"/lessons/{M1}/vocabulaire/complete").json()["cards_added"] == 0


def test_completed_grammar_lesson_appears_in_library(client: TestClient, seeded: Session) -> None:
    client.post(f"/lessons/{M1}/grammaire/complete")

    concepts = client.get("/library/concepts").json()

    assert [c["id"] for c in concepts] == [f"{M1}/pronoms-etre-avoir"]
