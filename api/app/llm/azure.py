from functools import cache
from pathlib import Path

import openai
from pydantic import BaseModel, Field

from app.domain.cost import Metered, Units
from app.domain.rubric import ErrorKind, Fix, RubricPass, TaggedError
from app.llm.grader import ProviderUnavailableError, WritingTask


class _Criterion(BaseModel):
    score: int = Field(ge=0, le=5)
    evidence: str


class _Criteria(BaseModel):
    task: _Criterion
    coherence: _Criterion
    vocabulary: _Criterion
    grammar: _Criterion


class _Fix(BaseModel):
    excerpt: str
    correction: str
    explanation: str


class _Error(BaseModel):
    tag: ErrorKind
    excerpt: str
    correction: str


class _RubricOutput(BaseModel):
    criteria: _Criteria
    fixes: list[_Fix]
    errors: list[_Error]


@cache
def _instructions() -> str:
    return (Path(__file__).parent / "prompts" / "grade_writing.md").read_text()


class AzureGrader:
    def __init__(self, client: openai.OpenAI, deployment: str) -> None:
        self._client = client
        self.model = deployment

    def grade_writing(self, task: WritingTask, text: str) -> Metered[RubricPass]:
        # Fixed rubric first, learner text last, so the long prefix is served from the cache.
        prompt = (
            f"Task {task.code} ({task.min_words}-{task.max_words} words):\n{task.prompt}\n\n"
            f"Learner's text:\n{text}"
        )
        try:
            response = self._client.responses.parse(
                model=self.model,
                instructions=_instructions(),
                input=prompt,
                text_format=_RubricOutput,
                reasoning={"effort": "low"},
            )
        except openai.APIError as exc:
            raise ProviderUnavailableError(str(exc)) from exc
        output = response.output_parsed
        if output is None or response.usage is None:
            raise ProviderUnavailableError("The grader returned no structured output")
        usage = response.usage
        cached = usage.input_tokens_details.cached_tokens
        units: Units = {
            "input_tokens": usage.input_tokens - cached,
            "cached_input_tokens": cached,
            "output_tokens": usage.output_tokens,
        }
        criteria = output.criteria.model_dump()
        return Metered(
            RubricPass(
                criteria={name: c["score"] for name, c in criteria.items()},
                evidence={name: c["evidence"] for name, c in criteria.items()},
                fixes=[Fix(f.excerpt, f.correction, f.explanation) for f in output.fixes],
                errors=[TaggedError(e.tag.value, e.excerpt, e.correction) for e in output.errors],
            ),
            units,
        )
