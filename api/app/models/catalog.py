from typing import Any

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Level(Base):
    __tablename__ = "levels"

    id: Mapped[str] = mapped_column(String(2), primary_key=True)
    order: Mapped[int] = mapped_column(unique=True)


class Block(Base):
    __tablename__ = "blocks"
    __table_args__ = (UniqueConstraint("level_id", "order"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    level_id: Mapped[str] = mapped_column(ForeignKey("levels.id"))
    order: Mapped[int]


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    block_id: Mapped[int] = mapped_column(ForeignKey("blocks.id"))
    order: Mapped[int] = mapped_column(unique=True)
    theme: Mapped[str]
    title: Mapped[str]
    summary: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))

    block: Mapped[Block] = relationship(lazy="joined")
    lessons: Mapped[list["Lesson"]] = relationship(order_by="Lesson.order", lazy="selectin")

    @property
    def level_id(self) -> str:
        return self.block.level_id


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    module_id: Mapped[str] = mapped_column(ForeignKey("modules.id"), index=True)
    order: Mapped[int]
    kind: Mapped[str] = mapped_column(String(20))
    title: Mapped[str]
    payload: Mapped[dict[str, Any]]


class Concept(Base):
    __tablename__ = "concepts"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    module_id: Mapped[str] = mapped_column(ForeignKey("modules.id"), index=True)
    title: Mapped[str]
    body_md: Mapped[str] = mapped_column(Text)


class Lexeme(Base):
    __tablename__ = "lexemes"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    module_id: Mapped[str] = mapped_column(ForeignKey("modules.id"), index=True)
    lemma: Mapped[str]
    pos: Mapped[str] = mapped_column(String(20))
    gender: Mapped[str | None] = mapped_column(String(1))
    en: Mapped[str]
    example_fr: Mapped[str]
    example_en: Mapped[str]


class Sentence(Base):
    __tablename__ = "sentences"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    module_id: Mapped[str] = mapped_column(ForeignKey("modules.id"), index=True)
    fr: Mapped[str] = mapped_column(Text)
    en: Mapped[str] = mapped_column(Text)


class Item(Base):
    """An assessable question. Live items are immutable; edits create a new version."""

    __tablename__ = "items"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    key: Mapped[str] = mapped_column(String(160), index=True)
    version: Mapped[int] = mapped_column(default=1)
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("items.id"))
    module_id: Mapped[str | None] = mapped_column(ForeignKey("modules.id"), index=True)
    skill: Mapped[str] = mapped_column(String(2))
    kind: Mapped[str] = mapped_column(String(20))
    cefr: Mapped[str] = mapped_column(String(2))
    difficulty: Mapped[float]
    payload: Mapped[dict[str, Any]]
    answer: Mapped[dict[str, Any]]
    content_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(10), default="live")


class ModuleGlossary(Base):
    """Hover translations for a module, generated once by the content pipeline."""

    __tablename__ = "module_glossaries"

    module_id: Mapped[str] = mapped_column(ForeignKey("modules.id"), primary_key=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    entries: Mapped[dict[str, Any]]


class RepeatSet(Base):
    """Ten model sentences for "Repeat after me", authored in content/repeat/."""

    __tablename__ = "repeat_sets"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    order: Mapped[int]
    title: Mapped[str]
    focus: Mapped[str]
    cefr: Mapped[str] = mapped_column(String(2))
    content_hash: Mapped[str] = mapped_column(String(64))


class RepeatSentence(Base):
    __tablename__ = "repeat_sentences"

    # Derived from the text, so an edited sentence gets a new id and its own audio clip.
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    set_id: Mapped[str] = mapped_column(ForeignKey("repeat_sets.id"), index=True)
    order: Mapped[int]
    fr: Mapped[str] = mapped_column(Text)
    en: Mapped[str] = mapped_column(Text)
    tip: Mapped[str] = mapped_column(Text)
