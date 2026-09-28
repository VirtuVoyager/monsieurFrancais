from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

EMBEDDING_DIMENSIONS = 512


class KbEntry(Base):
    """One searchable unit: a concept section, word, sentence, error or piece of feedback."""

    __tablename__ = "kb_entries"
    __table_args__ = (
        Index("ix_kb_entries_tsv", "tsv", postgresql_using="gin"),
        Index(
            "ix_kb_entries_title_norm",
            "title_norm",
            postgresql_using="gin",
            postgresql_ops={"title_norm": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(200), unique=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    module_id: Mapped[str | None] = mapped_column(ForeignKey("modules.id"))
    cefr: Mapped[str | None] = mapped_column(String(2))
    source_ref: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    # immutable_unaccent() is created in the migration: plain unaccent() isn't IMMUTABLE.
    tsv: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('french', immutable_unaccent(title || ' ' || text))", persisted=True),
    )
    title_norm: Mapped[str] = mapped_column(
        Text, Computed("immutable_unaccent(lower(title))", persisted=True)
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    embedding_model: Mapped[str | None] = mapped_column(String(60))
