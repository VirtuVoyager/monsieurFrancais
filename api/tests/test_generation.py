import re
import shutil
from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.audio import AudioRequest, dialogue_turns
from app.domain.cost import Metered
from app.domain.generation import (
    Batch,
    Draft,
    Verdict,
    bank_item,
    brief,
    check,
    parse_request,
    rebalance,
    settle,
    slugify,
)
from app.llm.writer import FakeItemWriter
from app.models import Item, UsageEvent
from app.services import drills, generation
from app.services.content import seed
from app.services.users import get_or_create_learner

WORDS = (15, 35)
DRAFT = Draft(
    slug="co-a1-gare",
    focus="heure",
    document=" ".join(["mot"] * 20),
    prompt="À quelle heure part le train ?",
    options=("10 h 15", "10 h 50", "9 h 15", "11 h"),
    answer=0,
    explanation="Le document dit dix heures quinze.",
)


def test_checks_catch_what_a_reviewer_should_never_have_to() -> None:
    assert check(DRAFT, WORDS, 4) == []
    assert check(replace(DRAFT, options=DRAFT.options[:3]), WORDS, 4) == ["3 options instead of 4"]
    assert check(replace(DRAFT, options=("a", "A ", "b", "c")), WORDS, 4) == [
        "two options are the same"
    ]
    assert check(replace(DRAFT, answer=4), WORDS, 4) == ["answer 4 is not an option"]
    assert check(replace(DRAFT, document="mot " * 60), WORDS, 4) == [
        "document has 60 words; expected 15 to 35"
    ]


def test_the_key_lands_on_a_position_set_by_the_slug_and_stays_correct() -> None:
    positions = set()
    for n in range(40):
        moved = rebalance(replace(DRAFT, slug=f"co-a1-{n}"))
        assert moved.options[moved.answer] == "10 h 15"
        assert sorted(moved.options) == sorted(DRAFT.options)
        assert rebalance(replace(DRAFT, slug=f"co-a1-{n}")) == moved
        positions.add(moved.answer)
    assert positions == {0, 1, 2, 3}


def test_the_review_verdict_and_the_checks_decide_together() -> None:
    corrected = replace(DRAFT, slug="", prompt="À quelle heure le train part-il ?")

    assert settle(DRAFT, Verdict("pass", [], None), WORDS, 4).status == "ok"
    fixed = settle(DRAFT, Verdict("fix", ["Inversion"], corrected), WORDS, 4)
    assert (fixed.status, fixed.draft.slug, fixed.issues) == ("fixed", "co-a1-gare", ["Inversion"])
    assert settle(DRAFT, Verdict("fix", ["x"], None), WORDS, 4).status == "rejected"
    broken = replace(corrected, options=("a", "b"))
    assert settle(DRAFT, Verdict("fix", ["x"], broken), WORDS, 4).status == "rejected"
    assert settle(DRAFT, Verdict("reject", ["Two keys"], None), WORDS, 4).status == "rejected"
    long_one = replace(DRAFT, document="mot " * 90)
    assert settle(long_one, Verdict("pass", [], None), WORDS, 4).status == "rejected"


def test_slugs_are_ascii_short_and_unique() -> None:
    taken = {"co-a1-retard-du-train"}

    assert slugify("CO", "A1", "Retard du train", taken) == "co-a1-retard-du-train-2"
    assert (
        slugify("CE", "B2", "Télétravail : avis d'un salarié", taken)
        == "ce-b2-teletravail-avis-d-un"
    )


def test_briefs_follow_the_exam_tasks_and_identical_batches_are_refused() -> None:
    tasks = yaml.safe_load((get_settings().content_dir / "exam_tasks.yaml").read_text())
    listening = brief(tasks, Batch("CO", "B2", 6, ("travail",)))
    reading = brief(tasks, Batch("CE", "A2", 6, ()))

    assert "100 to 190 words" in listening and "two voices" in listening
    assert "exactly 4" in reading and "two voices" not in reading
    batch = {"cefr": "A1", "count": 4, "themes": ["transports"]}
    with pytest.raises(ValueError, match="same thing"):
        parse_request({"skill": "CO", "batches": [batch, batch]})
    with pytest.raises(ValueError, match="No 'reply' format for CE"):
        parse_request({"skill": "CE", "batches": [{**batch, "format": "reply"}]})


def test_in_the_reply_format_the_replies_are_heard_and_only_letters_are_shown() -> None:
    reply = Batch("CO", "A1", 8, (), "reply")
    question = replace(DRAFT, document="Qu'est-ce que vous prenez au petit déjeuner ?", answer=2)

    item = bank_item(reply, question)

    assert item["audio_text"].splitlines() == [
        "Qu'est-ce que vous prenez au petit déjeuner ?",
        "A. 10 h 15",
        "B. 10 h 50",
        "C. 9 h 15",
        "D. 11 h",
    ]
    assert (item["options"], item["answer"]) == (
        ["Réponse A", "Réponse B", "Réponse C", "Réponse D"],
        2,
    )
    assert item["prompt"].startswith("Écoutez la question")
    assert bank_item(Batch("CE", "A1", 8, ()), DRAFT)["passage"] == DRAFT.document


def test_dialogues_alternate_two_voices_and_other_clips_keep_one() -> None:
    dialogue = AudioRequest("bank/co/x", "- Vous réglez comment ?\n- Par chèque.\n- Désolé.")
    voices = re.findall(r'<voice name="([^"]+)"', dialogue.ssml)

    assert dialogue_turns(dialogue.text) == ["Vous réglez comment ?", "Par chèque.", "Désolé."]
    assert len(voices) == 3 and voices[0] == voices[2] != voices[1]
    assert dialogue_turns("- Une seule ligne.") == []
    assert dialogue_turns("Bonjour.\n- Pas un dialogue.") == []
    assert len(re.findall("<voice", AudioRequest("k", "Le train part.").ssml)) == 1


@pytest.fixture
def content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    copy = tmp_path / "content"
    shutil.copytree(get_settings().content_dir, copy, ignore=shutil.ignore_patterns("drafts"))
    monkeypatch.setattr(get_settings(), "content_dir", copy)
    (copy / "generation").mkdir(exist_ok=True)
    request = {
        "skill": "CO",
        "batches": [
            {"cefr": "A2", "count": 3, "themes": ["transports"]},
            {"cefr": "B1", "count": 2, "themes": ["travail"]},
        ],
    }
    (copy / "generation" / "co-test.yaml").write_text(yaml.safe_dump(request))
    return copy


def test_batches_are_paid_once_and_promoted_into_a_live_bank(
    session: Session, content: Path
) -> None:
    user_id = get_or_create_learner(session).id
    request = content / "generation" / "co-test.yaml"

    first = generation.generate(session, user_id, request, FakeItemWriter())
    again = generation.generate(session, user_id, request, FakeItemWriter())

    assert len(first.written) == 2 and first.counts == {"ok": 5, "fixed": 0, "rejected": 0}
    assert again.written == [] and again.cached == 2
    events = session.scalars(select(UsageEvent).where(UsageEvent.feature == "content_gen"))
    assert len(list(events)) == 4
    assert generation.promote(request) == 5
    bank = yaml.safe_load((content / "items" / "co-test.yaml").read_text())
    assert bank["generated_from"] == "co-test"
    assert {i["slug"] for i in bank["items"]} == {
        "co-a2-document-1", "co-a2-document-2", "co-a2-document-3",
        "co-b1-document-1", "co-b1-document-2",
    }  # fmt: skip
    seed(session, content)
    live = {i.key for i in drills.bank(session, "CO")}
    assert "bank/co-test/co-a2-document-1" in live
    item = session.scalars(select(Item).where(Item.key == "bank/co-test/co-b1-document-2")).one()
    assert len(item.payload["options"]) == 4 and item.payload["audio_text"]


def test_rejected_items_stay_in_the_draft_and_hand_written_banks_are_protected(
    session: Session, content: Path
) -> None:
    class StrictReviewer(FakeItemWriter):
        def review(self, brief: str, drafts: list[Draft]) -> Metered[list[Verdict]]:
            verdicts = [Verdict("reject", ["Two keys"], None)] + [
                Verdict("pass", [], None) for _ in drafts[1:]
            ]
            return Metered(verdicts, {"input_tokens": 100})

    request = content / "generation" / "co-test.yaml"
    report = generation.generate(
        session, get_or_create_learner(session).id, request, StrictReviewer()
    )

    assert report.counts["rejected"] == 2
    assert generation.promote(request) == 3
    hand_written = content / "generation" / "co.yaml"
    hand_written.write_text(request.read_text())
    with pytest.raises(ValueError, match="by hand"):
        generation.promote(hand_written)
