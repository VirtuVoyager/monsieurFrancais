import unicodedata
from dataclasses import dataclass
from typing import Any

ANSWER_KEYS = ("answer", "accepted", "explanation")
# Typographic apostrophes and non-breaking spaces count as their plain forms.
_TYPOGRAPHY = {0x2019: "'", 0x2018: "'", 0x02BC: "'", 0x00A0: " ", 0x202F: " "}


@dataclass(frozen=True)
class CheckResult:
    correct: bool
    expected: str
    explanation: str | None = None


def normalize(text: str) -> str:
    """Case, spacing, apostrophe style and final punctuation don't matter; accents do."""
    text = unicodedata.normalize("NFC", text).translate(_TYPOGRAPHY)
    return " ".join(text.split()).casefold().rstrip(" .!?…")


def check(exercise: dict[str, Any], response: dict[str, Any]) -> CheckResult:
    kind = exercise["kind"]
    explanation = exercise.get("explanation")
    if kind == "mcq":
        expected_index = int(exercise["answer"])
        return CheckResult(
            correct=response.get("choice") == expected_index,
            expected=exercise["options"][expected_index],
            explanation=explanation,
        )
    if kind == "cloze":
        accepted = [normalize(a) for a in exercise["accepted"]]
        return CheckResult(
            correct=normalize(str(response.get("text", ""))) in accepted,
            expected=exercise["accepted"][0],
            explanation=explanation,
        )
    if kind == "order":
        return CheckResult(
            correct=normalize(str(response.get("text", ""))) == normalize(exercise["answer"]),
            expected=exercise["answer"],
            explanation=explanation,
        )
    raise ValueError(f"Unknown exercise kind: {kind}")


def public(exercise: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in exercise.items() if k not in ANSWER_KEYS}
