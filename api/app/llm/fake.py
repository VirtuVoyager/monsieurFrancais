import re

from app.domain.cost import Metered
from app.domain.rubric import CRITERIA, Fix, RubricPass, TaggedError, word_count
from app.llm.grader import SpokenTask, WritingTask

# A handful of classic learner errors, enough to exercise the pipeline without a model.
_RULES: list[tuple[re.Pattern[str], str, str, str]] = [
    (
        re.compile(r"\b(je suis|il est|elle est) (\w+) ans\b", re.I),
        "verb-choice",
        "j'ai {1} ans",
        "Age takes avoir, not être.",
    ),
    (
        re.compile(r"\b(il|elle) est (un|une) (\w+)", re.I),
        "article",
        "{0} est {2}",
        "No article before a profession after être.",
    ),
    (
        re.compile(r"\bpas (un|une|des) (\w+)", re.I),
        "negation",
        "pas de {1}",
        "After a negation, un/une/des becomes de.",
    ),
    (
        re.compile(r"\bje (ai|aime|habite|étudie|apprends)\b", re.I),
        "elision",
        "j'{0}",
        "Je becomes j' before a vowel.",
    ),
]
_CONNECTORS = ("mais", "parce que", "donc", "ensuite", "d'abord", "enfin", "cependant", "car")


class FakeGrader:
    model = "fake-text"

    def grade_writing(self, task: WritingTask, text: str) -> Metered[RubricPass]:
        words = word_count(text)
        matches = [
            (match, tag, fix.format(*match.groups()), why)
            for pattern, tag, fix, why in _RULES
            for match in pattern.finditer(text)
        ]
        errors = [TaggedError(tag, m.group(0), fixed) for m, tag, fixed, _ in matches]
        fixes = [Fix(m.group(0), fixed, why) for m, _, fixed, why in matches]
        lower = text.lower()
        tokens = re.findall(r"\w+", lower)
        criteria = {
            "task": _task_score(words, task),
            "coherence": min(1 + sum(c in lower for c in _CONNECTORS), 5),
            "vocabulary": min(max(round(5 * len(set(tokens)) / max(len(tokens), 1)), 1), 5),
            "grammar": max(5 - len(errors), 0 if not tokens else 1),
        }
        evidence = {c: text[:80] for c in CRITERIA}
        units = {"input_tokens": len(text) / 4 + 1500, "output_tokens": 400}
        return Metered(RubricPass(criteria, evidence, fixes[:3], errors), units)

    def grade_speaking(self, task: SpokenTask, transcript: str) -> Metered[RubricPass]:
        # Roughly 60 words a minute is a fluent A2 speaker; judge only the candidate's lines.
        spoken = " ".join(
            line.split(":", 1)[1] for line in transcript.splitlines() if line.startswith("Candidat")
        )
        words = round(task.seconds / 60 * 60)
        return self.grade_writing(WritingTask(task.code, task.prompt, words // 2, words), spoken)


def _task_score(words: int, task: WritingTask) -> int:
    if task.min_words <= words <= task.max_words:
        return 4
    if 0.8 * task.min_words <= words <= 1.2 * task.max_words:
        return 3
    return 1 if words else 0
