import hashlib
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

# Keep each model call's output bounded; the shared text prefix is served from the cache.
BATCH = 200
# Part of every content hash: bump it when the prompt or the rules below change.
VERSION = "2"

_WORD = re.compile(r"[^\W\d_](?:[^\W\d_]|['’-](?=[^\W\d_]))*")
_WORD_OR_PUNCT = re.compile(r"[^\W\d_](?:[^\W\d_]|['-](?=[^\W\d_]))*|[^\w\s]")
_ELISION = re.compile(r"^((?:[cdjlmnst]|qu|jusqu|lorsqu|puisqu)['’])(.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class Gloss:
    form: str
    lemma: str
    en: str


def normalize(form: str) -> str:
    """The lookup key, shared with the browser: lower case, straight apostrophes, NFC."""
    text = unicodedata.normalize("NFC", form).replace("’", "'").lower()
    return re.sub(r"'\s+", "'", " ".join(text.split()))


def forms_in(texts: Iterable[str]) -> list[str]:
    """Every word form to gloss, with elided pieces (j'ai: j'ai, j', ai) as separate forms."""
    seen: dict[str, None] = {}
    for text in texts:
        for match in _WORD.finditer(text):
            word = normalize(match.group(0))
            pieces = [word]
            elided = _ELISION.match(word)
            if elided:
                pieces += [elided.group(1), elided.group(2)]
            if "-" in word:
                pieces += [p for p in word.split("-") if p]
            for piece in pieces:
                if len(piece) > 1 or piece in ("a", "à", "y", "ô"):
                    seen.setdefault(piece, None)
    return list(seen)


def strings_in(value: Any) -> list[str]:
    """All text inside a lesson payload, however deeply nested."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in strings_in(v)]
    if isinstance(value, list):
        return [s for v in value for s in strings_in(v)]
    return []


def content_hash(texts: Iterable[str], model: str) -> str:
    digest = hashlib.sha256(f"{VERSION}:{model}".encode())
    for text in texts:
        digest.update(b"\0" + text.encode())
    return digest.hexdigest()


def batches(forms: list[str]) -> list[list[str]]:
    return [forms[i : i + BATCH] for i in range(0, len(forms), BATCH)]


def as_entries(glosses: Iterable[Gloss], text: str) -> dict[str, dict[str, str]]:
    """Stored and served shape: form → lemma and English. Untranslatable forms are dropped, and
    so are phrases the model proposed that do not actually occur in the text."""
    entries: dict[str, dict[str, str]] = {}
    haystack = f" {' '.join(_WORD_OR_PUNCT.findall(normalize(text)))} "
    for gloss in glosses:
        key, en = normalize(gloss.form), gloss.en.strip()
        if " " in key and f" {key} " not in haystack:
            continue
        if key and en and key not in entries:
            entries[key] = {"lemma": gloss.lemma.strip() or key, "en": en}
    return entries
