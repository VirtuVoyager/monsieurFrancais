from fastapi import APIRouter

from app.db import SessionDep
from app.models import Note, NoteItem
from app.schemas.learning import NoteDetail, NoteItemOut, NoteReview, NoteSummary, NoteUpload
from app.services import notes
from app.services.users import CurrentUser

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("")
def upload_note(body: NoteUpload, session: SessionDep, user: CurrentUser) -> NoteDetail:
    note = notes.upload(session, user.id, body.filename, body.text)
    return _detail(*notes.get_note(session, user.id, note.id))


@router.get("")
def list_notes(session: SessionDep, user: CurrentUser) -> list[NoteSummary]:
    return [_summary(note, counts) for note, counts in notes.notes_with_counts(session, user.id)]


@router.get("/{note_id}")
def get_note(note_id: int, session: SessionDep, user: CurrentUser) -> NoteDetail:
    return _detail(*notes.get_note(session, user.id, note_id))


@router.post("/{note_id}/review")
def review_note(
    note_id: int, body: NoteReview, session: SessionDep, user: CurrentUser
) -> NoteDetail:
    decisions = [notes.Decision(d.id, d.approve, d.fr, d.en, d.gender) for d in body.items]
    notes.review(session, user.id, note_id, decisions)
    return _detail(*notes.get_note(session, user.id, note_id))


def _summary(note: Note, counts: dict[str, int]) -> NoteSummary:
    return NoteSummary.model_validate(
        {
            **{c: getattr(note, c) for c in ("id", "title", "filename", "day", "status")},
            "created_at": note.created_at,
            **{status: counts.get(status, 0) for status in ("proposed", "approved", "rejected")},
        }
    )


def _detail(note: Note, items: list[NoteItem]) -> NoteDetail:
    counts = {s: sum(i.status == s for i in items) for s in ("proposed", "approved", "rejected")}
    return NoteDetail(
        **_summary(note, counts).model_dump(),
        body_md=note.body_md,
        items=[NoteItemOut.model_validate(i, from_attributes=True) for i in items],
    )
