import asyncio

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import mcp_server


def test_tools_are_registered() -> None:
    names = {tool.name for tool in asyncio.run(mcp_server.server.list_tools())}

    assert names == {"search_kb", "get_skill_levels", "get_error_fingerprint", "get_progress"}


def test_tools_read_the_learner_data(client: TestClient, seeded: Session) -> None:
    client.post(
        "/lessons/a1-01-se-presenter/ecriture/writing",
        json={"text": "Je suis trente ans et je habite à Pune."},
    )

    assert mcp_server.progress(seeded)["total_modules"] == 2
    assert mcp_server.skill_levels(seeded)["CO"] is None
    assert {e.tag for e in mcp_server.error_fingerprint(seeded)} >= {"verb-choice", "elision"}
    assert mcp_server.search_learned(seeded, "ville", "catalogue")[0].title == "ville"
