import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.audio import spoken
from app.domain.cost import Metered
from app.domain.notes import (
    MAX_WORDS,
    NoteEntry,
    capped,
    clean_markdown,
    day_of,
    gender_of,
    table_entries,
    title_of,
)
from app.llm.grader import ProviderUnavailableError
from app.llm.notes import FakeNoteExtractor
from app.models import Card, Note, NoteItem, UsageEvent, User
from app.services import audio, notes

NOTE = """# 🇫🇷 Day 5 — Class Notes (Le logement)

#french #tcf-tef #day5

[[Day 4 - Class notes|← Day 4]]

## 1. Il y a

> [!tip] Il y a never changes
> **Il y a** means "there is" and "there are": _il y a un parc_, _il y a deux chambres_.

## 🗂️ New Words

|French|Gender|Meaning|
|---|---|---|
|un appartement|masc.|a flat|
|la cuisine _(f.)_||a kitchen|
|un loyer||rent|
|—|—|—|

## Phrases

|French|Meaning|
|---|---|
|J'habite dans un appartement.|I live in a flat.|
|Il y a deux chambres.|There are two bedrooms.|

## ✅ Quick self-test

- [ ] Translate: there is a park.
"""


def test_titles_days_and_obsidian_syntax_are_cleaned() -> None:
    title = title_of("Day_5.md", NOTE)

    assert title == "Day 5 — Class Notes (Le logement)"
    assert day_of(title) == 5
    assert day_of("Jour 12 - vocabulaire") == 12
    assert title_of("Day_6_-_Vocab.md", "no heading") == "Day 6 - Vocab"
    cleaned = clean_markdown(NOTE)
    assert "[[" not in cleaned and "#tcf-tef" not in cleaned
    assert "> **Il y a never changes**" in cleaned
    assert "← Day 4" in cleaned


def test_genders_come_from_labels_notes_and_articles() -> None:
    assert (gender_of("masc."), gender_of("fém."), gender_of("masc./fem.")) == ("m", "f", None)
    words = {e.fr: e for e in table_entries(NOTE) if e.kind == "word"}

    assert (words["un appartement"].gender, words["la cuisine"].gender) == ("m", "f")
    assert words["un loyer"].gender == "m"
    assert "—" not in words


def test_offline_extraction_finds_words_phrases_and_grammar() -> None:
    entries = table_entries(NOTE)
    kinds = {kind: [e.fr for e in entries if e.kind == kind] for kind in ("word", "sentence")}

    assert kinds["word"] == ["un appartement", "la cuisine", "un loyer"]
    assert kinds["sentence"] == ["J'habite dans un appartement.", "Il y a deux chambres."]
    grammar = [e for e in entries if e.kind == "grammar"]
    assert [g.fr for g in grammar] == ["Il y a"]
    assert "there is" in grammar[0].detail


def test_caps_duplicates_and_non_sentence_examples_are_dropped() -> None:
    words = [NoteEntry("word", f"mot {i}", "word") for i in range(MAX_WORDS + 5)]
    kept = capped([*words, NoteEntry("word", "Mot 1", "again")])
    assert len(kept) == MAX_WORDS

    for not_a_sentence in ("grand → grande", "un salon de coiffure", "le coiffeur / la coiffeuse"):
        example = capped([NoteEntry("word", "grand", "big", detail=not_a_sentence)])
        assert example[0].detail == ""
    sentence = capped([NoteEntry("word", "grand", "big", detail="Il est très grand.")])
    assert sentence[0].detail == "Il est très grand."


def test_an_uploaded_note_is_extracted_metered_and_listed(
    client: TestClient, session: Session
) -> None:
    note = client.post("/notes", json={"filename": "Day_5.md", "text": NOTE}).json()

    assert (note["status"], note["day"], note["proposed"]) == ("ready", 5, 6)
    assert {i["kind"] for i in note["items"]} == {"word", "sentence", "grammar"}
    assert session.scalars(select(UsageEvent).where(UsageEvent.feature == "notes")).one()
    listed = client.get("/notes").json()
    assert [(n["id"], n["proposed"]) for n in listed] == [(note["id"], 6)]
    again = client.post("/notes", json={"filename": "copy.md", "text": NOTE}).json()
    assert again["id"] == note["id"]


def test_approved_items_reach_library_review_and_search(
    client: TestClient, session: Session
) -> None:
    note = client.post("/notes", json={"filename": "Day_5.md", "text": NOTE}).json()
    items = {i["fr"]: i for i in note["items"]}
    decisions = [
        {"id": items["un appartement"]["id"], "approve": True, "en": "an apartment"},
        {"id": items["la cuisine"]["id"], "approve": False},
        {"id": items["Il y a deux chambres."]["id"], "approve": True},
        {"id": items["Il y a"]["id"], "approve": True},
    ]

    reviewed = client.post(f"/notes/{note['id']}/review", json={"items": decisions}).json()

    assert (reviewed["approved"], reviewed["rejected"]) == (3, 1)
    words = {w["lemma"]: w for w in client.get("/library/words").json()}
    assert words["un appartement"]["en"] == "an apartment"
    assert words["un appartement"]["source"] == "Class notes · Day 5"
    assert "la cuisine" not in words
    sentences = [s["fr"] for s in client.get("/library/sentences", params={"q": "chambres"}).json()]
    assert sentences == ["Il y a deux chambres."]
    concepts = [c["title"] for c in client.get("/library/concepts").json()]
    assert "Il y a" in concepts
    due = {c["answer_fr"]: c for c in client.get("/reviews/due").json()}
    assert due["un appartement"]["prompt_en"] == "an apartment"
    assert due["un appartement"]["gender"] == "m"
    found = client.get("/search", params={"q": "appartement", "scope": "mine"}).json()
    assert any(hit["title"] == "un appartement" for hit in found)


def test_rejecting_an_approved_item_takes_it_back_out(client: TestClient, session: Session) -> None:
    note = client.post("/notes", json={"filename": "Day_5.md", "text": NOTE}).json()
    word = next(i for i in note["items"] if i["fr"] == "un loyer")
    url = f"/notes/{note['id']}/review"

    client.post(url, json={"items": [{"id": word["id"], "approve": True}]})
    client.post(url, json={"items": [{"id": word["id"], "approve": False}]})

    assert session.scalars(select(Card).where(Card.item_type == "note")).all() == []
    assert client.get("/search", params={"q": "loyer", "scope": "mine"}).json() == []


def test_items_from_an_earlier_note_are_not_offered_again(client: TestClient) -> None:
    client.post("/notes", json={"filename": "Day_5.md", "text": NOTE})
    later = (
        NOTE.replace("Day 5", "Day 6") + "\n|French|Meaning|\n|---|---|\n|un balcon|a balcony|\n"
    )

    note = client.post("/notes", json={"filename": "Day_6.md", "text": later}).json()

    assert [i["fr"] for i in note["items"]] == ["un balcon"]


def test_a_blocked_note_is_kept_and_extracted_later(
    client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(notes, "get_note_extractor", _Unavailable)
    note = client.post("/notes", json={"filename": "Day_5.md", "text": NOTE}).json()
    assert (note["status"], note["items"]) == ("pending", [])

    monkeypatch.setattr(notes, "get_note_extractor", FakeNoteExtractor)
    assert notes.extract_pending(session) == 1
    assert session.get_one(Note, note["id"]).status == "ready"


class _Unavailable(FakeNoteExtractor):
    def extract(self, title: str, markdown: str) -> Metered[list[NoteEntry]]:
        raise ProviderUnavailableError("down")


def test_notes_are_private(client: TestClient, session: Session) -> None:
    note = client.post("/notes", json={"filename": "Day_5.md", "text": NOTE}).json()
    theirs = "# Day 1\n|French|Meaning|\n|---|---|\n|oui|yes|\n"
    other = notes.upload(session, _other_user(session), "mine.md", theirs)

    assert client.get(f"/notes/{other.id}").status_code == 404
    item_id = session.scalars(select(NoteItem.id).where(NoteItem.note_id == other.id)).first()
    response = client.post(
        f"/notes/{note['id']}/review", json={"items": [{"id": item_id, "approve": True}]}
    )
    assert response.status_code == 404


def _other_user(session: Session) -> int:
    user = User(display_name="Someone else", passphrase_hash=None, settings={})
    session.add(user)
    session.commit()
    return user.id


def test_approved_words_get_audio_once_and_stay_out_of_the_manifest(
    client: TestClient, session: Session
) -> None:
    note = client.post("/notes", json={"filename": "Day_5.md", "text": NOTE}).json()
    items = {i["fr"]: i for i in note["items"]}
    approve = [items["un appartement"], items["Il y a deux chambres."], items["Il y a"]]
    client.post(
        f"/notes/{note['id']}/review",
        json={"items": [{"id": i["id"], "approve": True} for i in approve]},
    )

    first = audio.generate_notes(session)
    again = audio.generate_notes(session)

    assert (first.generated, again.generated, again.existing) == (2, 0, 2)  # grammar has none
    word = next(w for w in client.get("/library/words").json() if w["lemma"] == "un appartement")
    assert word["audio_url"].startswith("/media/catalog/audio/")
    due = {c["answer_fr"]: c for c in client.get("/reviews/due").json()}
    assert (
        due["Il y a deux chambres."]["audio_url"]
        == client.get("/library/sentences").json()[0]["audio_url"]
    )
    assert not get_settings().media_manifest.exists()


def test_pairs_are_spoken_with_a_pause() -> None:
    assert spoken("le boulanger / la boulangère") == "le boulanger, la boulangère"
    assert spoken("Bonjour !") == "Bonjour !"
