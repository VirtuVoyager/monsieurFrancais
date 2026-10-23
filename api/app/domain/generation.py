import hashlib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Literal

# Bump to regenerate every batch after a change to how briefs are built.
VERSION = 1
Status = Literal["ok", "fixed", "rejected"]
# Listening clips are synthesised with one voice, so a dialogue would sound like one person
# talking to themselves. Lift this once audio supports several speakers.
SINGLE_VOICE = (
    "The document is read aloud by a single voice: write one speaker (announcement, voicemail, "
    "radio segment, testimony, one side of an interview), never a dialogue."
)


@dataclass(frozen=True)
class Batch:
    skill: str
    cefr: str
    count: int
    themes: tuple[str, ...]

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
        Batch(skill, b["cefr"], int(b["count"]), tuple(b.get("themes", ()))) for b in raw["batches"]
    ]
    if len(set(batches)) != len(batches):
        # Identical batches share a cache key, so the second would silently never run.
        raise ValueError("Two batches ask for the same thing; give them different themes")
    return batches


def brief(tasks: dict[str, Any], batch: Batch) -> str:
    spec = tasks[batch.skill]
    level = spec["levels"][batch.cefr]
    low, high = level["words"]
    lines = [
        f"Exam: {tasks['exam']}, section {batch.skill}, level {batch.cefr}.",
        f"Language: {tasks['language']['standard']}.",
        f"Documents at this level: {', '.join(level['documents'])}.",
        f"What the question tests: {level['focus']}.",
        f"Document length: {low} to {high} words.",
        f"Options: exactly {spec['format']['options']}, one correct.",
        f"Themes for this batch: {', '.join(batch.themes) or 'any everyday subject'}.",
        "Item-writing rules:",
        *(f"- {rule}" for rule in tasks["mcq_rules"]["rules"]),
    ]
    if batch.skill == "CO":
        lines.append(SINGLE_VOICE)
    return "\n".join(lines)


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


def bank_item(skill: str, cefr: str, draft: Draft) -> dict[str, Any]:
    document = "audio_text" if skill == "CO" else "passage"
    return {
        "slug": draft.slug,
        "cefr": cefr,
        "origin": "generated",
        "focus": draft.focus,
        document: draft.document,
        "prompt": draft.prompt,
        "options": list(draft.options),
        "answer": draft.answer,
        "explanation": draft.explanation,
    }


def _normal(text: str) -> str:
    return " ".join(text.lower().split())
