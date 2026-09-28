import shutil
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.exercises import normalize
from app.models import AssessmentRun, Item, Lexeme, Module, Response
from app.services.content import discover, seed
from app.services.users import get_or_create_learner

REPO_CONTENT = get_settings().content_dir
SOURCES = discover(REPO_CONTENT)


def _exercises(source_meta: dict[str, Any], check_items: list[dict[str, Any]]) -> list[Any]:
    lesson_exercises = [
        ex
        for lesson in source_meta["lessons"]
        for ex in lesson.get("exercises", []) + lesson.get("questions", [])
    ]
    return lesson_exercises + check_items


def _words(text: str) -> list[str]:
    return sorted(normalize(t) for t in text.split() if any(c.isalnum() for c in t))


@pytest.mark.parametrize("source", SOURCES, ids=lambda s: s.slug)
def test_every_exercise_in_repo_content_is_well_formed(source: Any) -> None:
    for ex in _exercises(source.meta, source.check_items):
        if ex["kind"] == "mcq":
            assert 0 <= ex["answer"] < len(ex["options"]), ex
        elif ex["kind"] == "cloze":
            assert "___" in ex["prompt"] and ex["accepted"], ex
        elif ex["kind"] == "order":
            assert _words(" ".join(ex["words"])) == _words(ex["answer"]), ex
        else:
            pytest.fail(f"unknown kind {ex['kind']}")


@pytest.mark.parametrize("source", SOURCES, ids=lambda s: s.slug)
def test_grammar_lessons_reference_existing_concepts(source: Any) -> None:
    for lesson in source.meta["lessons"]:
        if lesson["kind"] == "grammar":
            assert lesson["concept"] in source.concepts


def test_seed_is_idempotent(session: Session) -> None:
    first = seed(session, REPO_CONTENT)
    second = seed(session, REPO_CONTENT)

    assert len(first.modules_updated) == len(SOURCES)
    assert second.modules_updated == []
    assert session.scalars(select(Lexeme).where(Lexeme.lemma == "sœur")).one().gender == "f"


def test_editing_an_answered_item_creates_a_new_version(session: Session, tmp_path: Path) -> None:
    content = tmp_path / "content"
    shutil.copytree(REPO_CONTENT, content)
    seed(session, content)
    item = session.scalars(select(Item).where(Item.key == "a1-02-la-famille/tante")).one()
    run = AssessmentRun(user_id=get_or_create_learner(session).id, kind="module_check")
    session.add(run)
    session.flush()
    session.add(Response(run_id=run.id, item_id=item.id, skill="VO", answer={"choice": 1}))
    session.flush()

    check = content / "modules/a1/02-la-famille/check.yaml"
    check.write_text(check.read_text().replace("La sœur de ma mère", "La sœur de mon père"))
    report = seed(session, content)

    versions = session.scalars(
        select(Item).where(Item.key == item.key).order_by(Item.version)
    ).all()
    assert report.items_versioned == 1
    assert [(v.version, v.status) for v in versions] == [(1, "retired"), (2, "live")]
    assert versions[1].supersedes_id == item.id


def test_removed_items_are_retired(session: Session, tmp_path: Path) -> None:
    content = tmp_path / "content"
    shutil.copytree(REPO_CONTENT, content)
    seed(session, content)
    check = content / "modules/a1/02-la-famille/check.yaml"
    check.write_text(
        "\n".join(line for line in check.read_text().splitlines() if "slug: cousin" not in line)
    )

    report = seed(session, content)

    assert report.items_retired == 1
    assert session.get(Module, "a1-02-la-famille") is not None
