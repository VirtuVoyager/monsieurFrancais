from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, CreatedAt


class Note(CreatedAt, Base):
    """A class note as uploaded; its study items wait for the learner's approval."""

    __tablename__ = "notes"
    __table_args__ = (UniqueConstraint("user_id", "content_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    filename: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(200))
    day: Mapped[int | None]
    body_md: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(10), default="pending")
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Hover translations for words the course glossaries do not already cover; None until built.
    glossary: Mapped[dict[str, Any] | None]


class NoteItem(CreatedAt, Base):
    __tablename__ = "note_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(ForeignKey("notes.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(10), default="proposed")
    fr: Mapped[str] = mapped_column(Text)
    en: Mapped[str] = mapped_column(Text, default="")
    gender: Mapped[str | None] = mapped_column(String(1))
    detail: Mapped[str] = mapped_column(Text, default="")
    key: Mapped[str] = mapped_column(String(300), index=True)
