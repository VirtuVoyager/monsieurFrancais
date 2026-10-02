from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.glossary import Gloss, as_entries, content_hash, forms_in, normalize
from app.llm.glosser import FakeGlosser
from app.models import Lesson, ModuleGlossary, Note, UsageEvent
from app.services import glossary
from app.services.users import get_or_create_learner

M1, M2 = "a1-01-se-presenter", "a1-02-la-famille"


def test_forms_keep_whole_words_and_their_elided_and_hyphenated_pieces() -> None:
    forms = forms_in(["J’ai 30 ans. Habite-t-elle ici ? Aujourd'hui, à Paris."])

    assert {"j'ai", "j'", "ai", "ans", "habite-t-elle", "habite", "elle", "à"} <= set(forms)
    assert "aujourd'hui" in forms
    assert "30" not in forms and "t" not in forms


def test_keys_are_normalised_and_untranslated_forms_dropped() -> None:
    assert normalize("S’ Appelle  Il") == "s'appelle il"
    glosses = [
        Gloss("Suis", "être", "(I) am"),
        Gloss("Paris", "Paris", ""),
        Gloss("il y a", "il y a", "there is"),
        Gloss("parce que", "parce que", "because"),
    ]

    entries = as_entries(glosses, "Je suis à Paris parce qu'il pleut. Parce que, oui !")

    assert entries == {
        "suis": {"lemma": "être", "en": "(I) am"},
        "parce que": {"lemma": "parce que", "en": "because"},
    }
    assert content_hash(["a"], "m1") != content_hash(["a"], "m2")


def test_module_glossaries_are_built_once_and_rebuilt_when_text_changes(
    seeded: Session,
) -> None:
    user_id = get_or_create_learner(seeded).id

    first = glossary.build_modules(seeded, user_id, FakeGlosser())
    again = glossary.build_modules(seeded, user_id, FakeGlosser())

    assert sorted(first.built) == [M1, M2] and again.built == []
    entries = seeded.get_one(ModuleGlossary, M1).entries
    assert entries["suis"] == {"lemma": "être", "en": "(I) am"}
    lesson = seeded.scalars(select(Lesson).where(Lesson.module_id == M1)).first()
    assert lesson is not None
    lesson.title = f"{lesson.title} (révisé)"
    seeded.commit()
    assert glossary.build_modules(seeded, user_id, FakeGlosser()).built == [M1]
    assert seeded.scalars(select(UsageEvent).where(UsageEvent.feature == "glossary")).first()


def test_the_learner_gets_glossaries_of_unlocked_modules_and_the_current_one(
    client: TestClient, seeded: Session
) -> None:
    glossary.build_modules(seeded, get_or_create_learner(seeded).id, FakeGlosser())

    unlocked = client.get("/glossary").json()
    current = client.get("/glossary", params={"module_id": M2}).json()

    assert unlocked == seeded.get_one(ModuleGlossary, M1).entries  # module 2 is still locked
    assert unlocked["suis"]["en"] == "(I) am"
    assert seeded.get_one(ModuleGlossary, M2).entries.items() <= current.items()


def test_a_note_glosses_only_words_the_course_does_not_cover(
    client: TestClient, seeded: Session
) -> None:
    glossary.build_modules(seeded, get_or_create_learner(seeded).id, FakeGlosser())
    text = "# Day 9\n\nJe suis à la maison. Il y a une famille et des amis.\n"

    note_id = client.post("/notes", json={"filename": "Day_9.md", "text": text}).json()["id"]

    built = seeded.get_one(Note, note_id).glossary
    assert built is not None
    assert "suis" not in built  # already in the course glossary
    assert built["il y a"]["en"] == "there is / there are"
    assert client.get("/glossary").json()["famille"]["en"] == "family"
