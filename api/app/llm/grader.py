from dataclasses import dataclass
from typing import Protocol

from app.domain.cost import Metered
from app.domain.rubric import RubricPass


@dataclass(frozen=True)
class WritingTask:
    code: str
    prompt: str
    min_words: int
    max_words: int


class GraderUnavailableError(Exception):
    """The provider could not grade right now; the submission stays queued."""


class Grader(Protocol):
    model: str

    def grade_writing(self, task: WritingTask, text: str) -> Metered[RubricPass]: ...
