from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, CreatedAt


class User(CreatedAt, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str]
    passphrase_hash: Mapped[str | None]
    settings: Mapped[dict[str, Any]] = mapped_column(default=dict)


class ModuleProgress(Base):
    __tablename__ = "module_progress"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    module_id: Mapped[str] = mapped_column(ForeignKey("modules.id"), primary_key=True)
    lessons_done: Mapped[list[Any]] = mapped_column(default=list)
    check_score: Mapped[float | None]
    status: Mapped[str] = mapped_column(String(10), default="open")
    covered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AssessmentRun(CreatedAt, Base):
    __tablename__ = "assessment_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    scope_id: Mapped[str | None] = mapped_column(String(160))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    score: Mapped[float | None]
    result: Mapped[dict[str, Any]] = mapped_column(default=dict)


class Response(CreatedAt, Base):
    __tablename__ = "responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("assessment_runs.id"), index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id"))
    skill: Mapped[str] = mapped_column(String(2))
    answer: Mapped[dict[str, Any]]
    correct: Mapped[bool | None]
    time_ms: Mapped[int | None]
    timed_out: Mapped[bool] = mapped_column(default=False)


class Card(CreatedAt, Base):
    __tablename__ = "cards"
    __table_args__ = (UniqueConstraint("user_id", "item_type", "item_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    item_type: Mapped[str] = mapped_column(String(10))
    item_id: Mapped[str] = mapped_column(String(160))
    fsrs_state: Mapped[dict[str, Any]]
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    reviews: Mapped[int] = mapped_column(default=0)


class WritingSubmission(CreatedAt, Base):
    __tablename__ = "writing_submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("assessment_runs.id"))
    lesson_id: Mapped[str | None] = mapped_column(String(160))
    item_id: Mapped[str | None] = mapped_column(ForeignKey("items.id"))
    task: Mapped[str] = mapped_column(String(4))
    prompt: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    word_count: Mapped[int]
    status: Mapped[str] = mapped_column(String(10), default="pending")
    score: Mapped[float | None]
    rubric: Mapped[dict[str, Any]] = mapped_column(default=dict)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ErrorTag(Base):
    __tablename__ = "error_tags"
    __table_args__ = (UniqueConstraint("user_id", "tag"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    tag: Mapped[str] = mapped_column(String(30))
    example: Mapped[str] = mapped_column(Text)
    correction: Mapped[str] = mapped_column(Text)
    count: Mapped[int] = mapped_column(default=0)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))
