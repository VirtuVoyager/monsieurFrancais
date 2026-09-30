import hashlib
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import ColumnElement, Select, case, delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.domain.ranking import reciprocal_rank_fusion
from app.llm import get_embedder
from app.llm.embedder import Embedder, Vector
from app.llm.grader import ProviderUnavailableError
from app.models import (
    Concept,
    ErrorTag,
    KbEntry,
    Lesson,
    Lexeme,
    Module,
    ModuleProgress,
    Sentence,
    WritingSubmission,
)
from app.services.budget import BudgetExceededError, price_book
from app.services.metering import run_metered

Scope = Literal["learned", "catalogue", "mine"]
CANDIDATES = 30
EMBED_BATCH = 64


@dataclass(frozen=True)
class Entry:
    key: str
    kind: str
    title: str
    text: str
    source_ref: str
    module_id: str | None = None
    cefr: str | None = None
    user_id: int | None = None


def index_catalogue(session: Session) -> int:
    lessons = {(ls.module_id, ls.kind): ls for ls in session.scalars(select(Lesson))}
    grammar_lessons = {
        (ls.module_id, ls.payload.get("concept")): ls
        for ls in lessons.values()
        if ls.kind == "grammar"
    }
    levels = {m.id: m.level_id for m in session.scalars(select(Module))}

    def link(module_id: str, kind: str) -> str:
        lesson = lessons.get((module_id, kind))
        return f"/lessons/{lesson.id}" if lesson else f"/modules/{module_id}"

    entries: list[Entry] = []
    for concept in session.scalars(select(Concept)):
        slug = concept.id.split("/", 1)[1]
        lesson = grammar_lessons.get((concept.module_id, slug))
        ref = f"/lessons/{lesson.id}" if lesson else f"/modules/{concept.module_id}"
        for i, section in enumerate(_sections(concept.body_md)):
            heading, _, body = section.partition("\n")
            entries.append(
                Entry(
                    f"concept:{concept.id}#{i}",
                    "grammar",
                    f"{concept.title} · {heading}",
                    body.strip(),
                    ref,
                    concept.module_id,
                    levels[concept.module_id],
                )
            )
    for word in session.scalars(select(Lexeme)):
        gender = f" ({word.gender})" if word.gender else ""
        entries.append(
            Entry(
                f"word:{word.id}",
                "word",
                word.lemma,
                f"{word.lemma}{gender}: {word.en}. {word.example_fr} {word.example_en}",
                link(word.module_id, "vocab"),
                word.module_id,
                levels[word.module_id],
            )
        )
    for sentence in session.scalars(select(Sentence)):
        entries.append(
            Entry(
                f"sentence:{sentence.id}",
                "sentence",
                sentence.fr,
                sentence.en,
                link(sentence.module_id, "sentences"),
                sentence.module_id,
                levels[sentence.module_id],
            )
        )
    _upsert(session, entries)
    session.execute(
        delete(KbEntry).where(
            KbEntry.user_id.is_(None), KbEntry.key.not_in([e.key for e in entries])
        )
    )
    return len(entries)


def index_user(session: Session, user_id: int) -> None:
    entries = [
        Entry(
            f"error:{user_id}:{e.tag}",
            "error",
            e.tag,
            f"{e.example} → {e.correction} (seen {e.count} times)",
            "/library",
            user_id=user_id,
        )
        for e in session.scalars(select(ErrorTag).where(ErrorTag.user_id == user_id))
    ]
    graded = session.scalars(
        select(WritingSubmission).where(
            WritingSubmission.user_id == user_id, WritingSubmission.status == "graded"
        )
    )
    for submission in graded:
        ref = f"/lessons/{submission.lesson_id}" if submission.lesson_id else "/drills"
        for i, fix in enumerate(submission.rubric.get("fixes", [])):
            entries.append(
                Entry(
                    f"fix:{submission.id}:{i}",
                    "feedback",
                    fix["correction"],
                    f"{fix['excerpt']} → {fix['correction']}. {fix['explanation']}",
                    ref,
                    user_id=user_id,
                )
            )
    _upsert(session, entries)


def search(
    session: Session, user_id: int, query: str, scope: Scope, kind: str | None = None
) -> list[KbEntry]:
    text = query.strip()
    if not text:
        return []
    base = select(KbEntry.key).where(_scope_filter(user_id, scope))
    if kind:
        base = base.where(KbEntry.kind == kind)
    normalized = func.immutable_unaccent(func.lower(text))
    tsquery = func.websearch_to_tsquery("french", func.immutable_unaccent(text))
    full_text = session.scalars(
        base.where(KbEntry.tsv.op("@@")(tsquery))
        .order_by(func.ts_rank_cd(KbEntry.tsv, tsquery).desc())
        .limit(CANDIDATES)
    ).all()
    # Trigram and prefix matching catch typos and partial words that stemming misses.
    fuzzy = session.scalars(
        base.where(
            or_(KbEntry.title_norm.op("%")(normalized), KbEntry.title_norm.startswith(normalized))
        )
        .order_by(func.similarity(KbEntry.title_norm, normalized).desc())
        .limit(CANDIDATES)
    ).all()
    semantic = _semantic(session, user_id, base, text)
    ranked = reciprocal_rank_fusion(list(full_text), list(fuzzy), semantic)[:20]
    rows = {e.key: e for e in session.scalars(select(KbEntry).where(KbEntry.key.in_(ranked)))}
    return [rows[key] for key in ranked]


def embed_pending(session: Session, user_id: int, embedder: Embedder | None = None) -> int:
    """Embeds entries that are new, changed, or from an older embedding model."""
    embedder = embedder or get_embedder()
    done = 0
    while True:
        batch = session.scalars(
            select(KbEntry)
            .where(or_(KbEntry.embedding.is_(None), KbEntry.embedding_model != embedder.model))
            .order_by(KbEntry.id)
            .limit(EMBED_BATCH)
        ).all()
        if not batch:
            return done
        texts = [f"{e.title}\n{e.text}" for e in batch]
        vectors = _embed(session, user_id, embedder, texts, feature="embeddings")
        for entry, vector in zip(batch, vectors, strict=True):
            entry.embedding = vector
            entry.embedding_model = embedder.model
        session.commit()
        done += len(batch)


def _semantic(session: Session, user_id: int, base: Select[str], text: str) -> list[str]:
    """Nearest entries by meaning; search still works on keywords if embedding is unavailable."""
    embedder = get_embedder()
    try:
        [vector] = _embed(session, user_id, embedder, [text], feature="search")
    except (BudgetExceededError, ProviderUnavailableError):
        return []
    return list(
        session.scalars(
            base.where(KbEntry.embedding_model == embedder.model)
            .order_by(KbEntry.embedding.cosine_distance(vector))
            .limit(CANDIDATES)
        )
    )


def _embed(
    session: Session, user_id: int, embedder: Embedder, texts: list[str], feature: str
) -> list[Vector]:
    estimate = (
        price_book()
        .for_model(embedder.model)
        .cost({"input_tokens": sum(len(t) for t in texts) / 3})
    )
    return run_metered(
        session,
        user_id=user_id,
        feature=feature,
        model=embedder.model,
        estimate_usd=estimate,
        call=lambda: embedder.embed(texts),
    )


def _scope_filter(user_id: int, scope: Scope) -> ColumnElement[bool]:
    mine = KbEntry.user_id == user_id
    if scope == "mine":
        return mine
    catalogue = KbEntry.user_id.is_(None)
    if scope == "catalogue":
        return catalogue
    started = select(ModuleProgress.module_id).where(
        ModuleProgress.user_id == user_id,
        or_(
            func.jsonb_array_length(ModuleProgress.lessons_done) > 0,
            ModuleProgress.status == "placed",
        ),
    )
    return or_(mine, catalogue & KbEntry.module_id.in_(started))


def _upsert(session: Session, entries: list[Entry]) -> None:
    if not entries:
        return
    rows = [
        {**e.__dict__, "content_hash": hashlib.sha256(f"{e.title}\n{e.text}".encode()).hexdigest()}
        for e in entries
    ]
    stmt = insert(KbEntry).values(rows)
    changed = KbEntry.content_hash != stmt.excluded.content_hash
    session.execute(
        stmt.on_conflict_do_update(
            index_elements=["key"],
            set_={
                "title": stmt.excluded.title,
                "text": stmt.excluded.text,
                "source_ref": stmt.excluded.source_ref,
                "module_id": stmt.excluded.module_id,
                "cefr": stmt.excluded.cefr,
                "content_hash": stmt.excluded.content_hash,
                # Changed text needs a fresh embedding.
                "embedding": case((changed, None), else_=KbEntry.embedding),
                "embedding_model": case((changed, None), else_=KbEntry.embedding_model),
            },
        )
    )


def _sections(markdown: str) -> list[str]:
    parts = [p.strip() for p in ("\n" + markdown).split("\n## ") if p.strip()]
    return parts or [markdown]
