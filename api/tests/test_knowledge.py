from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import KbEntry
from app.services import knowledge
from app.services.knowledge import Entry


def _titles(client: TestClient, q: str, scope: str = "catalogue") -> list[str]:
    return [hit["title"] for hit in client.get("/search", params={"q": q, "scope": scope}).json()]


def test_catalogue_is_indexed_when_content_is_seeded(seeded: Session) -> None:
    kinds = set(seeded.scalars(select(KbEntry.kind)))

    assert kinds == {"grammar", "word", "sentence"}


def test_search_ignores_accents_and_finds_words(client: TestClient, seeded: Session) -> None:
    assert "sœur" in _titles(client, "soeur")
    assert "ville" in _titles(client, "ville")


def test_search_tolerates_typos_and_english(client: TestClient, seeded: Session) -> None:
    assert "ville" in _titles(client, "vile")
    assert "grand-mère" in _titles(client, "grandmother")


def test_grammar_sections_are_searchable(client: TestClient, seeded: Session) -> None:
    hits = client.get("/search", params={"q": "négation pas de", "scope": "catalogue"}).json()

    assert hits[0]["kind"] == "grammar"
    assert hits[0]["source_ref"] == "/lessons/a1-02-la-famille/grammaire"


def test_learned_scope_only_covers_started_modules(client: TestClient, seeded: Session) -> None:
    assert _titles(client, "ville", scope="learned") == []

    client.post("/lessons/a1-01-se-presenter/grammaire/complete")

    assert "ville" in _titles(client, "ville", scope="learned")
    assert "sœur" not in _titles(client, "soeur", scope="learned")


def test_graded_writing_makes_errors_searchable(client: TestClient, seeded: Session) -> None:
    client.post(
        "/lessons/a1-01-se-presenter/ecriture/writing",
        json={"text": "Je suis trente ans et il est un ingénieur à Pune."},
    )

    hits = client.get("/search", params={"q": "trente ans", "scope": "mine"}).json()

    assert hits and all(hit["personal"] for hit in hits)
    assert {hit["kind"] for hit in hits} <= {"error", "feedback"}


def test_changed_text_clears_its_embedding(seeded: Session) -> None:
    entry = seeded.scalars(select(KbEntry).where(KbEntry.key.startswith("word:"))).first()
    assert entry is not None
    entry.embedding = [0.1] * 512
    entry.embedding_model = "text-embedding-3-small"
    seeded.flush()

    knowledge._upsert(
        seeded,
        [Entry(entry.key, entry.kind, entry.title, entry.text + " (edited)", entry.source_ref)],
    )
    seeded.expire_all()

    refreshed = seeded.get_one(KbEntry, entry.id)
    assert refreshed.embedding is None and refreshed.embedding_model is None


def test_empty_query_returns_nothing(client: TestClient, seeded: Session) -> None:
    assert client.get("/search", params={"q": "  "}).json() == []
