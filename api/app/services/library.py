from datetime import UTC, datetime
from typing import Any, cast

import fsrs
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Card, Lesson, Lexeme, Sentence

_scheduler = fsrs.Scheduler()
CARD_SOURCES: dict[str, type[Lexeme] | type[Sentence]] = {"vocab": Lexeme, "sentences": Sentence}
ITEM_TYPES = {Lexeme: "lexeme", Sentence: "sentence"}


def enroll_lesson(session: Session, user_id: int, lesson: Lesson) -> int:
    """Completing a vocab or sentences lesson puts its items into the review queue."""
    source = CARD_SOURCES.get(lesson.kind)
    if source is None:
        return 0
    ids = session.scalars(select(source.id).where(source.module_id == lesson.module_id)).all()
    return enroll(session, user_id, ITEM_TYPES[source], list(ids))


def enroll(session: Session, user_id: int, item_type: str, ids: list[str]) -> int:
    if not ids:
        return 0
    now = datetime.now(UTC)
    rows = [
        {
            "user_id": user_id,
            "item_type": item_type,
            "item_id": item_id,
            "fsrs_state": _state(fsrs.Card(due=now)),
            "due_at": now,
        }
        for item_id in ids
    ]
    inserted = session.scalars(
        insert(Card).values(rows).on_conflict_do_nothing().returning(Card.id)
    )
    return len(inserted.all())


def unenroll(session: Session, user_id: int, item_type: str, ids: list[str]) -> None:
    session.execute(
        delete(Card).where(
            Card.user_id == user_id, Card.item_type == item_type, Card.item_id.in_(ids)
        )
    )


def due_cards(session: Session, user_id: int, limit: int, now: datetime) -> list[Card]:
    return list(
        session.scalars(
            select(Card)
            .where(Card.user_id == user_id, Card.due_at <= now)
            .order_by(Card.due_at)
            .limit(limit)
        )
    )


def review(session: Session, user_id: int, card_id: int, rating: int, now: datetime) -> Card:
    card = session.get(Card, card_id)
    if card is None or card.user_id != user_id:
        raise NotFoundError("Card not found")
    current = fsrs.Card.from_dict(cast(Any, card.fsrs_state))
    updated, _ = _scheduler.review_card(current, fsrs.Rating(rating), now)
    card.fsrs_state = _state(updated)
    card.due_at = updated.due
    card.reviews += 1
    session.commit()
    return card


def _state(card: fsrs.Card) -> dict[str, Any]:
    return dict(card.to_dict())
