import csv
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from app.domain.scales import CEFR_DIFFICULTY, CEFR_LEVELS
from app.models import Block, Concept, Item, Lesson, Level, Lexeme, Module, Response, Sentence

ITEM_FIELDS_PUBLIC = ("prompt", "options", "words")
ITEM_FIELDS_ANSWER = ("answer", "accepted", "explanation")


@dataclass(frozen=True)
class ModuleSource:
    meta: dict[str, Any]
    concepts: dict[str, tuple[str, str]]
    vocab: list[dict[str, str]]
    sentences: list[dict[str, str]]
    check_items: list[dict[str, Any]]
    content_hash: str

    @property
    def slug(self) -> str:
        return str(self.meta["slug"])


@dataclass
class SeedReport:
    modules_updated: list[str] = field(default_factory=list)
    items_created: int = 0
    items_versioned: int = 0
    items_retired: int = 0


def load_module(path: Path) -> ModuleSource:
    files = sorted(p for p in path.rglob("*") if p.is_file())
    digest = hashlib.sha256()
    for file in files:
        digest.update(file.relative_to(path).as_posix().encode())
        digest.update(file.read_bytes())
    concepts = {}
    for md in sorted((path / "concepts").glob("*.md")):
        title, _, body = md.read_text().partition("\n")
        concepts[md.stem] = (title.removeprefix("# ").strip(), body.strip())
    return ModuleSource(
        meta=yaml.safe_load((path / "module.yaml").read_text()),
        concepts=concepts,
        vocab=_read_csv(path / "vocab.csv"),
        sentences=_read_csv(path / "sentences.csv"),
        check_items=yaml.safe_load((path / "check.yaml").read_text())["items"],
        content_hash=digest.hexdigest(),
    )


def discover(content_dir: Path) -> list[ModuleSource]:
    return [
        load_module(p.parent) for p in sorted((content_dir / "modules").glob("*/*/module.yaml"))
    ]


def seed(session: Session, content_dir: Path) -> SeedReport:
    report = SeedReport()
    for order, cefr in enumerate(CEFR_LEVELS, start=1):
        session.merge(Level(id=cefr, order=order))
    for source in discover(content_dir):
        module = session.get(Module, source.slug)
        if module is not None and module.content_hash == source.content_hash:
            continue
        _upsert_module(session, source, module)
        _sync_items(session, source, report)
        report.modules_updated.append(source.slug)
    session.commit()
    return report


def _upsert_module(session: Session, source: ModuleSource, module: Module | None) -> None:
    meta, slug = source.meta, source.slug
    block = _block(session, meta["level"], int(meta["block"]))
    if module is None:
        module = Module(id=slug)
        session.add(module)
    module.block_id = block.id
    module.order = int(meta["order"])
    module.theme = meta["theme"]
    module.title = meta["title"]
    module.summary = meta["summary"].strip()
    module.content_hash = source.content_hash
    session.flush()

    for model in (Lesson, Concept, Lexeme, Sentence):
        session.execute(delete(model).where(model.module_id == slug))
    for order, lesson in enumerate(meta["lessons"], start=1):
        payload = {k: v for k, v in lesson.items() if k not in ("slug", "kind", "title")}
        session.add(
            Lesson(
                id=f"{slug}/{lesson['slug']}",
                module_id=slug,
                order=order,
                kind=lesson["kind"],
                title=lesson["title"],
                payload=payload,
            )
        )
    for concept_slug, (title, body) in source.concepts.items():
        session.add(Concept(id=f"{slug}/{concept_slug}", module_id=slug, title=title, body_md=body))
    for row in source.vocab:
        session.add(
            Lexeme(
                id=f"{slug}/{row['lemma']}",
                module_id=slug,
                lemma=row["lemma"],
                pos=row["pos"],
                gender=row["gender"] or None,
                en=row["en"],
                example_fr=row["example_fr"],
                example_en=row["example_en"],
            )
        )
    for row in source.sentences:
        sentence_id = hashlib.sha1(row["fr"].encode()).hexdigest()[:10]
        session.add(
            Sentence(id=f"{slug}/{sentence_id}", module_id=slug, fr=row["fr"], en=row["en"])
        )


def _sync_items(session: Session, source: ModuleSource, report: SeedReport) -> None:
    cefr = source.meta["level"]
    wanted_keys = set()
    for raw in source.check_items:
        key = f"{source.slug}/{raw['slug']}"
        wanted_keys.add(key)
        fields = {
            "module_id": source.slug,
            "skill": raw["skill"],
            "kind": raw["kind"],
            "cefr": raw.get("cefr", cefr),
            "difficulty": float(raw.get("difficulty", CEFR_DIFFICULTY[raw.get("cefr", cefr)])),
            "payload": {k: raw[k] for k in ITEM_FIELDS_PUBLIC if k in raw},
            "answer": {k: raw[k] for k in ITEM_FIELDS_ANSWER if k in raw},
        }
        content_hash = hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()
        _upsert_item(session, key, fields, content_hash, report)

    stale = session.scalars(
        select(Item).where(
            Item.module_id == source.slug, Item.status == "live", Item.key.not_in(wanted_keys)
        )
    )
    for item in stale:
        item.status = "retired"
        report.items_retired += 1


def _upsert_item(
    session: Session, key: str, fields: dict[str, Any], content_hash: str, report: SeedReport
) -> None:
    latest = session.scalar(select(Item).where(Item.key == key).order_by(Item.version.desc()))
    if latest is None:
        session.add(Item(id=f"{key}@v1", key=key, version=1, content_hash=content_hash, **fields))
        report.items_created += 1
        return
    if latest.content_hash == content_hash:
        latest.status = "live"
        return
    answered = session.scalar(select(exists().where(Response.item_id == latest.id)))
    if not answered:
        for name, value in fields.items():
            setattr(latest, name, value)
        latest.content_hash = content_hash
        latest.status = "live"
        return
    # Answered items are immutable so past responses keep pointing at what was shown.
    latest.status = "retired"
    version = latest.version + 1
    session.add(
        Item(
            id=f"{key}@v{version}",
            key=key,
            version=version,
            supersedes_id=latest.id,
            content_hash=content_hash,
            **fields,
        )
    )
    report.items_versioned += 1


def _block(session: Session, level: str, order: int) -> Block:
    block = session.scalar(select(Block).where(Block.level_id == level, Block.order == order))
    if block is None:
        block = Block(level_id=level, order=order)
        session.add(block)
        session.flush()
    return block


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))
