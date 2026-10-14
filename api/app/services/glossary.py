from dataclasses import dataclass, field
from functools import partial
from typing import Any

import structlog
from sqlalchemy import ScalarResult, select
from sqlalchemy.orm import Session

from app.domain.coverage import Status
from app.domain.glossary import (
    Gloss,
    as_entries,
    batches,
    content_hash,
    forms_in,
    strings_in,
)
from app.domain.notes import clean_markdown
from app.llm import get_glosser
from app.llm.glosser import Glosser
from app.llm.grader import ProviderUnavailableError
from app.models import (
    Concept,
    Lexeme,
    Module,
    ModuleGlossary,
    Note,
    Sentence,
)
from app.services.budget import BudgetExceededError, price_book
from app.services.metering import run_metered
from app.services.path import load_path

log = structlog.get_logger()
PROMPT_TOKENS = 700
OUTPUT_TOKENS_PER_FORM = 30

Entries = dict[str, Any]


@dataclass
class GlossaryReport:
    built: list[str] = field(default_factory=list)
    unchanged: int = 0


def module_texts(session: Session, module: Module) -> list[str]:
    texts = [module.title, module.summary]
    for lesson in module.lessons:
        texts += [lesson.title, *strings_in(lesson.payload)]
    texts += [
        f"{c.title}\n{c.body_md}"
        for c in session.scalars(select(Concept).where(Concept.module_id == module.id))
    ]
    for word in session.scalars(select(Lexeme).where(Lexeme.module_id == module.id)):
        texts += [word.lemma, word.example_fr]
    texts += session.scalars(select(Sentence.fr).where(Sentence.module_id == module.id))
    return texts


def build_modules(session: Session, user_id: int, glosser: Glosser | None = None) -> GlossaryReport:
    """Content pipeline step: a module's glossary is paid for only when its text changes."""
    glosser = glosser or get_glosser()
    report = GlossaryReport()
    for module in session.scalars(select(Module).order_by(Module.order)):
        texts = module_texts(session, module)
        digest = content_hash(texts, glosser.model)
        current = session.get(ModuleGlossary, module.id)
        if current and current.content_hash == digest:
            report.unchanged += 1
            continue
        entries = _gloss(session, user_id, glosser, texts, known=set())
        if current is None:
            session.add(ModuleGlossary(module_id=module.id, content_hash=digest, entries=entries))
        else:
            current.content_hash, current.entries = digest, entries
        session.commit()
        report.built.append(module.id)
    return report


def build_note(session: Session, note: Note, glosser: Glosser | None = None) -> bool:
    """Glosses only the words of a class note that the course glossaries do not cover."""
    glosser = glosser or get_glosser()
    known = set(_module_entries(session, note.user_id))
    try:
        note.glossary = _gloss(
            session, note.user_id, glosser, [clean_markdown(note.body_md)], known
        )
    except (BudgetExceededError, ProviderUnavailableError) as exc:
        log.warning("note_glossary_deferred", note_id=note.id, reason=str(exc))
        return False
    session.commit()
    return True


def for_learner(session: Session, user_id: int, module_id: str | None = None) -> Entries:
    """Every gloss the learner may meet; the current module's meanings win over others."""
    merged: Entries = {}
    notes: ScalarResult[Entries | None] = session.scalars(
        select(Note.glossary).where(Note.user_id == user_id, Note.glossary.is_not(None))
    )
    for glossary in notes:
        merged.update(glossary or {})
    merged.update(_module_entries(session, user_id))
    if module_id:
        current = session.get(ModuleGlossary, module_id)
        merged.update(current.entries if current else {})
    return merged


def _module_entries(session: Session, user_id: int) -> Entries:
    # Only modules the learner can open, so the payload grows with their path, not the course.
    view = load_path(session, user_id)
    unlocked = [m.id for m in view.modules if view.status[m.id] != Status.LOCKED]
    merged: Entries = {}
    rows: ScalarResult[Entries] = session.scalars(
        select(ModuleGlossary.entries).where(ModuleGlossary.module_id.in_(unlocked))
    )
    for entries in rows:
        merged.update(entries)
    return merged


def _gloss(
    session: Session, user_id: int, glosser: Glosser, texts: list[str], known: set[str]
) -> Entries:
    text = "\n".join(t for t in texts if t)
    forms = [f for f in forms_in(texts) if f not in known]
    pricing = price_book().for_model(glosser.model)
    glosses: list[Gloss] = []
    # The first batch also collects fixed phrases; a note with no new words still gets them.
    for index, batch in enumerate(batches(forms) or [[]]):
        estimate = pricing.cost(
            {
                "input_tokens": PROMPT_TOKENS + len(text) / 3,
                "output_tokens": OUTPUT_TOKENS_PER_FORM * (len(batch) + 20),
            }
        )
        glosses += run_metered(
            session,
            user_id=user_id,
            feature="glossary",
            model=glosser.model,
            estimate_usd=estimate,
            call=partial(glosser.gloss, text, batch, index == 0),
        )
    return as_entries(glosses, text)
