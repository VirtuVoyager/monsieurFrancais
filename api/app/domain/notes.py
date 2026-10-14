import re
from dataclasses import dataclass, replace
from pathlib import PurePath
from typing import Literal

Kind = Literal["word", "sentence", "grammar"]

# Caps keep one runaway note from flooding the approval screen and the review queue.
MAX_WORDS = 150
MAX_SENTENCES = 60
MAX_GRAMMAR = 15

_WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
_CALLOUT = re.compile(r"^(>\s*)\[!\w+\][+-]?\s*(.*)$", re.MULTILINE)
_TAG_LINE = re.compile(r"^\s*(#[\w-]+\s*)+$", re.MULTILINE)
_DAY = re.compile(r"\b(?:day|jour)\s*(\d{1,3})\b", re.IGNORECASE)
_GENDER_NOTE = re.compile(r"\s*_?\((m|f)\.\)_?\s*")
_ARTICLE_GENDER = {"un": "m", "le": "m", "une": "f", "la": "f"}
_SELF_TEST = re.compile(r"self-test|homework|devoirs", re.IGNORECASE)


@dataclass(frozen=True)
class NoteEntry:
    kind: Kind
    fr: str
    en: str = ""
    gender: str | None = None
    # A word's example sentence, or a grammar point's explanation in Markdown.
    detail: str = ""


def title_of(filename: str, markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            title = re.sub(r"^[^\w«]+", "", line[2:]).strip()
            if title:
                return title
    return PurePath(filename).stem.replace("_", " ").strip()


def day_of(title: str) -> int | None:
    match = _DAY.search(title)
    return int(match.group(1)) if match else None


def clean_markdown(markdown: str) -> str:
    """Plain Markdown: Obsidian links become text, callouts become bold-titled quotes."""
    text = _WIKILINK.sub(lambda m: m.group(2) or m.group(1), markdown)
    text = _CALLOUT.sub(lambda m: f"{m.group(1)}**{m.group(2)}**" if m.group(2) else "", text)
    return _TAG_LINE.sub("", text).strip()


def key_of(text: str) -> str:
    # Accents are kept: "ou" and "où" are different entries.
    return " ".join(text.lower().split()).strip(" .!?;:,")


def gender_of(label: str) -> str | None:
    label = label.strip().lower()
    if label.startswith(("masc", "m.")) and "fem" not in label and "fém" not in label:
        return "m"
    if label.startswith(("fem", "fém", "f.")) and "masc" not in label:
        return "f"
    return None


def table_entries(markdown: str) -> list[NoteEntry]:
    """Offline extraction: French/Meaning table rows and `##` sections, no model needed."""
    entries: list[NoteEntry] = []
    for section in _sections(clean_markdown(markdown)):
        heading, body = section
        rows = _french_rows(body)
        entries += rows
        if not rows and heading and not _SELF_TEST.search(heading):
            title = re.sub(r"^\d+\.\s*", "", heading)
            entries.append(NoteEntry("grammar", title, detail=body.strip()))
    return capped(entries)


def is_sentence(text: str) -> bool:
    text = text.strip()
    return (
        len(text.split()) >= 3
        and text.endswith((".", "!", "?", "…"))
        and not any(mark in text for mark in ("→", "·", "|", " / "))
    )


def capped(entries: list[NoteEntry]) -> list[NoteEntry]:
    limits = {"word": MAX_WORDS, "sentence": MAX_SENTENCES, "grammar": MAX_GRAMMAR}
    seen: set[tuple[str, str]] = set()
    kept: list[NoteEntry] = []
    for entry in entries:
        identity = (entry.kind, key_of(entry.fr))
        if not identity[1] or identity in seen or limits[entry.kind] == 0:
            continue
        seen.add(identity)
        limits[entry.kind] -= 1
        drop_example = entry.kind == "word" and not is_sentence(entry.detail)
        kept.append(replace(entry, detail="") if drop_example else entry)
    return kept


def _sections(markdown: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    heading, lines = "", list[str]()
    for line in markdown.splitlines():
        if line.startswith("## "):
            sections.append((heading, "\n".join(lines)))
            heading, lines = re.sub(r"^[^\w«]+", "", line[3:]).strip(), []
        else:
            lines.append(line)
    sections.append((heading, "\n".join(lines)))
    return [(h, b) for h, b in sections if b.strip()]


def _french_rows(body: str) -> list[NoteEntry]:
    entries: list[NoteEntry] = []
    header: list[str] | None = None
    for line in body.splitlines():
        if not line.strip().startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue
        if header is None:
            header = [c.lower() for c in cells]
            continue
        row = dict(zip(header, cells, strict=False))
        entry = _row_entry(row)
        if entry:
            entries.append(entry)
    return entries


def _row_entry(row: dict[str, str]) -> NoteEntry | None:
    french, meaning = row.get("french", ""), row.get("meaning", "")
    if not french or not meaning or french in ("—", "-"):
        return None
    gender = gender_of(row.get("gender", ""))
    note = _GENDER_NOTE.search(french)
    if note:
        gender = gender or note.group(1)
        french = _GENDER_NOTE.sub(" ", french).strip()
    meaning = re.sub(r"\s*_\(.*?\)_", "", meaning).strip()
    if len(french.split()) >= 4 or french.rstrip().endswith((".", "!", "?")):
        return NoteEntry("sentence", french, meaning)
    return NoteEntry(
        "word", french, meaning, gender or _ARTICLE_GENDER.get(french.split()[0].lower())
    )
