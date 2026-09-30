from dataclasses import dataclass, field
from enum import StrEnum
from statistics import median

CRITERIA = ("task", "coherence", "vocabulary", "grammar")
MAX_PER_CRITERION = 5  # four criteria sum to the TCF /20 scale
MAX_FIXES = 3
DISAGREEMENT = 1.0  # points on /20 before a third pass is needed


class ErrorKind(StrEnum):
    AGREEMENT_GENDER = "agreement-gender"
    AGREEMENT_NUMBER = "agreement-number"
    VERB_CONJUGATION = "verb-conjugation"
    VERB_CHOICE = "verb-choice"
    TENSE_CHOICE = "tense-choice"
    SUBJUNCTIVE = "subjunctive"
    ARTICLE = "article"
    PREPOSITION = "preposition"
    NEGATION = "negation"
    PRONOUN = "pronoun"
    ELISION = "elision"
    WORD_ORDER = "word-order"
    SPELLING_ACCENT = "spelling-accent"
    REGISTER = "register"
    VOCABULARY_CHOICE = "vocabulary-choice"
    CONNECTOR = "connector"
    PUNCTUATION = "punctuation"


@dataclass(frozen=True)
class Fix:
    excerpt: str
    correction: str
    explanation: str


@dataclass(frozen=True)
class TaggedError:
    tag: str
    excerpt: str
    correction: str


@dataclass(frozen=True)
class RubricPass:
    criteria: dict[str, int]
    evidence: dict[str, str]
    fixes: list[Fix] = field(default_factory=list)
    errors: list[TaggedError] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(self.criteria.values())


@dataclass(frozen=True)
class Rubric:
    criteria: dict[str, float]
    evidence: dict[str, str]
    fixes: list[Fix]
    errors: list[TaggedError]
    passes: int

    @property
    def score(self) -> float:
        return sum(self.criteria.values())


def needs_another_pass(passes: list[RubricPass]) -> bool:
    return len(passes) == 2 and abs(passes[0].total - passes[1].total) > DISAGREEMENT


def combine(passes: list[RubricPass]) -> Rubric:
    """Median per criterion; feedback comes from the pass closest to the combined score."""
    if not passes:
        raise ValueError("At least one grading pass is required")
    criteria = {c: float(median(p.criteria[c] for p in passes)) for c in CRITERIA}
    total = sum(criteria.values())
    closest = min(passes, key=lambda p: abs(p.total - total))
    return Rubric(
        criteria=criteria,
        evidence=closest.evidence,
        fixes=closest.fixes[:MAX_FIXES],
        errors=closest.errors,
        passes=len(passes),
    )


def word_count(text: str) -> int:
    # French elisions (j'ai, l'école) count as two words, as on the exam.
    return len(text.replace("'", " ").replace("’", " ").split())
