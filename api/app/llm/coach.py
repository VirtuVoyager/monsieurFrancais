from functools import cache
from pathlib import Path
from typing import Protocol

import openai

from app.domain.cost import Metered, Units
from app.domain.pronunciation import MAX_ATTEMPTS, WordScore, weak_sounds
from app.llm.grader import ProviderUnavailableError


class Coach(Protocol):
    model: str

    def coach(
        self, sentence: str, tip: str, weak: list[WordScore], attempt: int
    ) -> Metered[str]: ...


def fallback(weak: list[WordScore]) -> str:
    """Said when the coach is unavailable, so the loop still tells the learner where to look."""
    words = ", ".join(f"« {w.word} »" for w in weak)
    return f"Listen to the slow version again and focus on {words}."


class FakeCoach:
    model = "fake-text"

    def coach(self, sentence: str, tip: str, weak: list[WordScore], attempt: int) -> Metered[str]:
        return Metered(f"{fallback(weak)} {tip}", {"input_tokens": 300, "output_tokens": 60})


def evidence(sentence: str, tip: str, weak: list[WordScore], attempt: int) -> str:
    lines = [
        f"Sentence: {sentence}",
        f"What this sentence practises: {tip}",
        f"Attempt {attempt} of {MAX_ATTEMPTS}.",
        "Words the assessment marked (accuracy out of 100; weak sound positions, 1-based):",
    ]
    for word in weak:
        positions = ", ".join(map(str, weak_sounds(word))) or "none singled out"
        problem = f", {word.error.lower()}" if word.error else ""
        lines.append(f"- {word.word}: {word.accuracy:.0f}{problem}; weak sounds: {positions}")
    return "\n".join(lines)


@cache
def _instructions() -> str:
    return (Path(__file__).parent / "prompts" / "coach_pronunciation.md").read_text()


class AzureCoach:
    def __init__(self, client: openai.OpenAI, deployment: str) -> None:
        self._client = client
        self.model = deployment

    def coach(self, sentence: str, tip: str, weak: list[WordScore], attempt: int) -> Metered[str]:
        try:
            response = self._client.responses.create(
                model=self.model,
                instructions=_instructions(),
                input=evidence(sentence, tip, weak, attempt),
                reasoning={"effort": "low"},
            )
        except openai.APIError as exc:
            raise ProviderUnavailableError(str(exc)) from exc
        if response.usage is None or not response.output_text:
            raise ProviderUnavailableError("The coach returned no text")
        usage = response.usage
        cached = usage.input_tokens_details.cached_tokens
        units: Units = {
            "input_tokens": usage.input_tokens - cached,
            "cached_input_tokens": cached,
            "output_tokens": usage.output_tokens,
        }
        return Metered(response.output_text.strip(), units)
