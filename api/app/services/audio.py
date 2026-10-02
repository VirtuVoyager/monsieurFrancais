import csv
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.audio import PRACTICE_RATE, AudioRequest, media_path, spoken
from app.domain.notes import key_of
from app.models import Item, Lesson, Lexeme, NoteItem, Sentence
from app.services.budget import price_book
from app.services.metering import run_metered
from app.speech import get_synthesizer
from app.speech.synthesizer import Synthesizer

MANIFEST_FIELDS = ("hash", "engine", "voice", "rate", "characters", "bytes", "key", "text")


@dataclass
class AudioReport:
    generated: int = 0
    existing: int = 0
    characters: int = 0


def item_request(item: Item) -> AudioRequest | None:
    text = item.payload.get("audio_text")
    return AudioRequest(item.key, text) if text else None


def lesson_request(lesson: Lesson) -> AudioRequest | None:
    text = lesson.payload.get("transcript") if lesson.kind == "listening" else None
    return AudioRequest(lesson.id, text) if text else None


def word_request(word: Lexeme) -> AudioRequest:
    return AudioRequest(word.id, word.lemma, PRACTICE_RATE)


def sentence_request(sentence: Sentence) -> AudioRequest:
    return AudioRequest(sentence.id, sentence.fr, PRACTICE_RATE)


def url_for(request: AudioRequest | None) -> str | None:
    """Served only once generated; until then the web app falls back to the browser voice."""
    if request is None:
        return None
    relative = media_path(request.content_hash(get_synthesizer().model))
    return f"/media/{relative}" if (get_settings().media_dir / relative).exists() else None


def catalogue_requests(session: Session) -> list[AudioRequest]:
    live_items = session.scalars(select(Item).where(Item.status == "live"))
    requests = [r for r in map(item_request, live_items) if r]
    requests += [r for r in map(lesson_request, session.scalars(select(Lesson))) if r]
    requests += [word_request(w) for w in session.scalars(select(Lexeme))]
    requests += [sentence_request(s) for s in session.scalars(select(Sentence))]
    return requests


def generate_missing(
    session: Session, user_id: int, synthesizer: Synthesizer | None = None
) -> AudioReport:
    """Content pipeline step: synthesise each clip once; an existing hash is never paid again."""
    requests = [(user_id, r) for r in catalogue_requests(session)]
    return _synthesize(session, requests, "tts_listening", synthesizer, manifest=True)


def note_request(item: NoteItem) -> AudioRequest | None:
    if item.kind not in ("word", "sentence"):
        return None
    # Keyed by text, so the same phrase approved from two notes shares one clip.
    return AudioRequest(f"note:{key_of(item.fr)}", spoken(item.fr), PRACTICE_RATE)


def generate_notes(session: Session, synthesizer: Synthesizer | None = None) -> AudioReport:
    """Clips for approved class-note words and phrases; kept out of the committed manifest."""
    approved = session.scalars(select(NoteItem).where(NoteItem.status == "approved"))
    requests = [(item.user_id, r) for item in approved if (r := note_request(item))]
    return _synthesize(session, requests, "tts_notes", synthesizer, manifest=False)


def _synthesize(
    session: Session,
    requests: list[tuple[int, AudioRequest]],
    feature: str,
    synthesizer: Synthesizer | None,
    *,
    manifest: bool,
) -> AudioReport:
    synthesizer = synthesizer or get_synthesizer()
    settings = get_settings()
    pricing = price_book().for_model(synthesizer.model)
    report = AudioReport()
    for user_id, request in requests:
        content_hash = request.content_hash(synthesizer.model)
        target = settings.media_dir / media_path(content_hash)
        if target.exists():
            report.existing += 1
            continue
        audio = run_metered(
            session,
            user_id=user_id,
            feature=feature,
            model=synthesizer.model,
            estimate_usd=pricing.cost({"characters": len(request.text)}),
            call=partial(synthesizer.synthesize, request),
        )
        _write_atomically(target, audio)
        if manifest:
            _append_manifest(
                settings.media_manifest, request, synthesizer, content_hash, len(audio)
            )
        report.generated += 1
        report.characters += len(request.text)
    return report


def _write_atomically(target: Path, data: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".part")
    partial.write_bytes(data)
    partial.replace(target)


def _append_manifest(
    path: Path, request: AudioRequest, synthesizer: Synthesizer, content_hash: str, size: int
) -> None:
    new = not path.exists()
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        if new:
            writer.writeheader()
        writer.writerow(
            {
                "hash": content_hash,
                "engine": synthesizer.model,
                "voice": request.voice.name,
                "rate": request.rate,
                "characters": len(request.text),
                "bytes": size,
                "key": request.key,
                "text": request.text.strip(),
            }
        )
