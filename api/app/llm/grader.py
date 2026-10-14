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


@dataclass(frozen=True)
class SpokenTask:
    code: str
    prompt: str
    seconds: int


class ProviderUnavailableError(Exception):
    """The provider could not answer right now; the work stays queued for a retry."""


class Grader(Protocol):
    model: str

    def grade_writing(self, task: WritingTask, text: str) -> Metered[RubricPass]: ...

    def grade_speaking(self, task: SpokenTask, transcript: str) -> Metered[RubricPass]: ...
