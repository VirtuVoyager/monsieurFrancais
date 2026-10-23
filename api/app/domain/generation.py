import hashlib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Literal

# Bump to regenerate every batch after a change to how briefs are built.
VERSION = 1
Status = Literal["ok", "fixed", "rejected"]
Format = Literal["document", "reply"]
# In the "reply" format the document is just the question heard before the four replies.
REPLY_WORDS = (3, 30)
REPLY_PROMPT = (
    "Écoutez la question et les quatre réponses. "
    "Choisissez la réponse qui correspond à la question."
)
LETTERS = "ABCD"
DIALOGUE = (
    'A dialogue is written one turn per line, each line starting with "- ", between a woman and a '
    "man: the woman speaks first, then they alternate, and each line agrees with its speaker's "
    "gender. It is read with two voices. A monologue has no dashes."
)


@dataclass(frozen=True)
class Batch:
    skill: str
    cefr: str
    count: int
    themes: tuple[str, ...]
    format: Format = "document"

    def key(self, brief: str, instructions: str, model: str) -> str:
        """What the batch was asked for: the same request is never paid for twice."""
        parts = [str(VERSION), model, instructions, brief, json.dumps(asdict(self))]
        return hashlib.sha256("\0".join(parts).encode()).hexdigest()


@dataclass(frozen=True)
class Draft:
    """A generated multiple-choice item, before checks and review."""

    slug: str
    focus: str
    document: str
    prompt: str
    options: tuple[str, ...]
    answer: int
    explanation: str


@dataclass
class Outcome:
    draft: Draft
    status: Status
    issues: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Verdict:
    verdict: Literal["pass", "fix", "reject"]
    issues: list[str]
    corrected: Draft | None


def parse_request(raw: dict[str, Any]) -> list[Batch]:
    skill = raw["skill"]
    batches = [
        Batch(
            skill,
            b["cefr"],
            int(b["count"]),
            tuple(b.get("themes", ())),
            b.get("format", "document"),
        )
        for b in raw["batches"]
    ]
    for batch in batches:
        if batch.format not in ("document", "reply") or (batch.format == "reply" and skill != "CO"):
            raise ValueError(f"No {batch.format!r} format for {skill}")
    if len(set(batches)) != len(batches):
        # Identical batches share a cache key, so the second would silently never run.
        raise ValueError("Two batches ask for the same thing; give them different themes")
    return batches


def brief(tasks: dict[str, Any], batch: Batch) -> str:
    spec = tasks[batch.skill]
    level = spec["levels"][batch.cefr]
    low, high = words_for(tasks, batch)
    lines = [
        f"Exam: {tasks['exam']}, section {batch.skill}, level {batch.cefr}.",
        f"Language: {tasks['language']['standard']}.",
    ]
    if batch.format == "reply":
        lines += [
            f"Format: {spec['formats']['reply']['task'].strip()}",
            "The document is the question that is heard, a natural question or remark someone "
            "would say to the listener. The options are the four replies, all heard: one is the "
            "natural answer; the others are well-formed replies to a different question.",
        ]
    else:
        lines += [
            f"Documents at this level: {', '.join(level['documents'])}.",
            f"What the question tests: {level['focus']}.",
        ]
        if batch.skill == "CO":
            lines += [
                f"Format: {spec['formats']['document']['task'].strip()}",
                "The question is asked after the recording, which is heard once.",
                DIALOGUE,
            ]
    lines += [
        f"Document length: {low} to {high} words.",
        f"Options: exactly {spec['format']['options']}, one correct.",
        f"Themes for this batch: {', '.join(batch.themes) or 'any everyday subject'}.",
        "Item-writing rules:",
        *(f"- {rule}" for rule in tasks["mcq_rules"]["rules"]),
    ]
    return "\n".join(lines)


def words_for(tasks: dict[str, Any], batch: Batch) -> tuple[int, int]:
    if batch.format == "reply":
        return REPLY_WORDS
    low, high = tasks[batch.skill]["levels"][batch.cefr]["words"]
    return int(low), int(high)


def check(draft: Draft, words: tuple[int, int], options: int) -> list[str]:
    """Problems a reviewer should never have to spot; any one of them rejects the item."""
    problems = []
    if len(draft.options) != options:
        problems.append(f"{len(draft.options)} options instead of {options}")
    if len({_normal(o) for o in draft.options}) != len(draft.options):
        problems.append("two options are the same")
    if not 0 <= draft.answer < len(draft.options):
        problems.append(f"answer {draft.answer} is not an option")
    if any(not o.strip() for o in (*draft.options, draft.prompt, draft.document)):
        problems.append("an empty field")
    count = len(draft.document.split())
    low, high = words
    # A little slack: the generator counts words loosely, and the exam's lengths are not exact.
    if not low * 0.8 <= count <= high * 1.2:
        problems.append(f"document has {count} words; expected {low} to {high}")
    return problems


def rebalance(draft: Draft) -> Draft:
    """Moves the key to a position fixed by the slug: generators favour putting it first."""
    position = int(hashlib.sha1(draft.slug.encode()).hexdigest(), 16) % len(draft.options)
    key = draft.options[draft.answer]
    others = [o for i, o in enumerate(draft.options) if i != draft.answer]
    others.insert(position, key)
    return replace(draft, options=tuple(others), answer=position)


def slugify(skill: str, cefr: str, hint: str, taken: set[str]) -> str:
    ascii_hint = unicodedata.normalize("NFKD", hint).encode("ascii", "ignore").decode()
    words = re.sub(r"[^a-z0-9]+", "-", ascii_hint.lower()).strip("-").split("-")[:4]
    base = "-".join([skill.lower(), cefr.lower(), *filter(None, words)])
    slug, n = base, 2
    while slug in taken:
        slug, n = f"{base}-{n}", n + 1
    taken.add(slug)
    return slug


def settle(draft: Draft, verdict: Verdict, words: tuple[int, int], options: int) -> Outcome:
    """Combines the deterministic checks with the reviewer's verdict on one item."""
    problems = check(draft, words, options)
    if verdict.verdict == "reject":
        return Outcome(draft, "rejected", problems + verdict.issues)
    if verdict.verdict == "fix":
        if verdict.corrected is None:
            return Outcome(draft, "rejected", [*verdict.issues, "no correction given"])
        fixed = replace(verdict.corrected, slug=draft.slug)
        if fixed_problems := check(fixed, words, options):
            return Outcome(draft, "rejected", verdict.issues + fixed_problems)
        return Outcome(rebalance(fixed), "fixed", verdict.issues)
    if problems:
        return Outcome(draft, "rejected", problems)
    return Outcome(rebalance(draft), "ok")


def bank_item(batch: Batch, draft: Draft) -> dict[str, Any]:
    document, prompt, options = draft.document, draft.prompt, list(draft.options)
    if batch.format == "reply":
        # As in the exam, the replies are heard, not read: the paper shows only the letters.
        spoken = [f"{letter}. {option}" for letter, option in zip(LETTERS, options, strict=False)]
        document = "\n".join([document, *spoken])
        prompt, options = REPLY_PROMPT, [f"Réponse {letter}" for letter in LETTERS[: len(options)]]
    return {
        "slug": draft.slug,
        "cefr": batch.cefr,
        "origin": "generated",
        "focus": draft.focus,
        "audio_text" if batch.skill == "CO" else "passage": document,
        "prompt": prompt,
        "options": options,
        "answer": draft.answer,
        "explanation": draft.explanation,
    }


def _normal(text: str) -> str:
    return " ".join(text.lower().split())
