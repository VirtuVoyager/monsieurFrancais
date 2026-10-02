import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.notes import clean_markdown, day_of, key_of, title_of
from app.errors import NotFoundError
from app.llm import get_note_extractor
from app.llm.grader import ProviderUnavailableError
from app.llm.notes import NoteExtractor
from app.models import Note, NoteItem
from app.services import glossary, knowledge, library
from app.services.budget import BudgetExceededError, price_book
from app.services.metering import run_metered

log = structlog.get_logger()

CARD_TYPE = "note"
# Upper bounds for one note's extraction, so the reservation always covers the call.
PROMPT_TOKENS = 900
MAX_OUTPUT_TOKENS = 12_000


@dataclass(frozen=True)
class Decision:
    item_id: int
    approve: bool
    fr: str | None = None
    en: str | None = None
    gender: str | None = None


def upload(session: Session, user_id: int, filename: str, text: str) -> Note:
    """Saves the note first, so nothing is lost if extraction is blocked; re-uploads are no-ops."""
    content_hash = hashlib.sha256(text.encode()).hexdigest()
    existing = session.scalar(
        select(Note).where(Note.user_id == user_id, Note.content_hash == content_hash)
    )
    if existing:
        return existing
    title = title_of(filename, text)
    note = Note(
        user_id=user_id,
        filename=filename,
        title=title[:200],
        day=day_of(title) or day_of(filename),
        body_md=text,
        content_hash=content_hash,
    )
    session.add(note)
    session.commit()
    try_extract(session, note)
    return note


def try_extract(session: Session, note: Note, extractor: NoteExtractor | None = None) -> bool:
    extractor = extractor or get_note_extractor()
    markdown = clean_markdown(note.body_md)
    estimate = (
        price_book()
        .for_model(extractor.model)
        .cost(
            {"input_tokens": PROMPT_TOKENS + len(markdown) / 3, "output_tokens": MAX_OUTPUT_TOKENS}
        )
    )
    try:
        entries = run_metered(
            session,
            user_id=note.user_id,
            feature="notes",
            model=extractor.model,
            estimate_usd=estimate,
            call=lambda: extractor.extract(note.title, markdown),
        )
    except (BudgetExceededError, ProviderUnavailableError) as exc:
        log.warning("notes_extraction_deferred", note_id=note.id, reason=str(exc))
        return False
    # Items already proposed or approved from an earlier note are not offered twice.
    known = {
        (kind, key)
        for kind, key in session.execute(
            select(NoteItem.kind, NoteItem.key).where(
                NoteItem.user_id == note.user_id, NoteItem.status != "rejected"
            )
        ).all()
    }
    for entry in entries:
        key = key_of(entry.fr)[:300]
        if (entry.kind, key) in known:
            continue
        session.add(
            NoteItem(
                note_id=note.id,
                user_id=note.user_id,
                kind=entry.kind,
                fr=entry.fr,
                en=entry.en,
                gender=entry.gender,
                detail=entry.detail,
                key=key,
            )
        )
    note.status = "ready"
    note.extracted_at = datetime.now(UTC)
    session.commit()
    glossary.build_note(session, note)
    return True


def extract_pending(session: Session) -> int:
    """Retries notes and note glossaries deferred by a budget cap or an unavailable model."""
    pending = session.scalars(select(Note).where(Note.status == "pending")).all()
    done = sum(try_extract(session, note) for note in pending)
    unglossed = session.scalars(
        select(Note).where(Note.status == "ready", Note.glossary.is_(None))
    ).all()
    return done + sum(glossary.build_note(session, note) for note in unglossed)


def notes_with_counts(session: Session, user_id: int) -> list[tuple[Note, dict[str, int]]]:
    counts: dict[int, dict[str, int]] = {}
    rows = session.execute(
        select(NoteItem.note_id, NoteItem.status, func.count())
        .where(NoteItem.user_id == user_id)
        .group_by(NoteItem.note_id, NoteItem.status)
    ).all()
    for note_id, status, count in rows:
        counts.setdefault(note_id, {})[status] = count
    notes = session.scalars(
        select(Note).where(Note.user_id == user_id).order_by(Note.day.desc().nulls_last(), Note.id)
    )
    return [(note, counts.get(note.id, {})) for note in notes]


def get_note(session: Session, user_id: int, note_id: int) -> tuple[Note, list[NoteItem]]:
    note = session.get(Note, note_id)
    if note is None or note.user_id != user_id:
        raise NotFoundError("Note not found")
    items = session.scalars(
        select(NoteItem).where(NoteItem.note_id == note_id).order_by(NoteItem.id)
    ).all()
    return note, list(items)


def review(session: Session, user_id: int, note_id: int, decisions: list[Decision]) -> None:
    """Approved words and sentences join the review queue; rejecting one takes it back out."""
    _, items = get_note(session, user_id, note_id)
    by_id = {item.id: item for item in items}
    for decision in decisions:
        item = by_id.get(decision.item_id)
        if item is None:
            raise NotFoundError(f"Item {decision.item_id} is not in this note")
        if decision.fr is not None and decision.fr.strip():
            item.fr = decision.fr.strip()
            item.key = key_of(item.fr)[:300]
        if decision.en is not None:
            item.en = decision.en.strip()
        if decision.gender is not None:
            item.gender = decision.gender or None
        item.status = "approved" if decision.approve else "rejected"
    cards = [i for i in items if i.kind in ("word", "sentence")]
    library.enroll(
        session, user_id, CARD_TYPE, [str(i.id) for i in cards if i.status == "approved"]
    )
    library.unenroll(
        session, user_id, CARD_TYPE, [str(i.id) for i in cards if i.status == "rejected"]
    )
    knowledge.index_user(session, user_id)
    session.commit()


def approved(session: Session, user_id: int, kind: str) -> list[tuple[NoteItem, Note]]:
    rows = session.execute(
        select(NoteItem, Note)
        .join(Note, Note.id == NoteItem.note_id)
        .where(NoteItem.user_id == user_id, NoteItem.kind == kind, NoteItem.status == "approved")
        .order_by(NoteItem.fr)
    ).all()
    return [(item, note) for item, note in rows]


def source_label(note: Note) -> str:
    return f"Class notes · Day {note.day}" if note.day else f"Class notes · {note.title}"
