import hashlib
import re
from functools import cache
from pathlib import Path
from typing import Literal, Protocol

import openai
from openai.types.responses import ResponseUsage
from pydantic import BaseModel

from app.domain.cost import Metered, Units
from app.domain.generation import Draft, Verdict
from app.llm.grader import ProviderUnavailableError

# Hard ceiling per call, so the budget reservation always covers what a call can cost.
MAX_OUTPUT_TOKENS = 24_000
PROMPTS = Path(__file__).parent / "prompts"


class ItemWriter(Protocol):
    model: str
    # Changes whenever the instructions do, so a reworded prompt regenerates its batches.
    fingerprint: str

    def write(self, brief: str, count: int, avoid: list[str]) -> Metered[list[Draft]]:
        """Drafts carry a short title in `slug`; the caller turns it into a unique slug."""
        ...

    def review(self, brief: str, drafts: list[Draft]) -> Metered[list[Verdict]]: ...


class FakeItemWriter:
    model = "fake-text"
    fingerprint = "fake"

    def write(self, brief: str, count: int, avoid: list[str]) -> Metered[list[Draft]]:
        found = re.search(r"Document length: (\d+) to (\d+) words", brief)
        words = int(found.group(1)) + 1 if found else 30
        drafts = [
            Draft(
                slug=f"document {n}",
                focus="information concrète",
                document=" ".join(["mot"] * words),
                prompt=f"Question {n} ?",
                options=("Réponse A", "Réponse B", "Réponse C", "Réponse D"),
                answer=0,
                explanation="La réponse A est dans le document.",
            )
            for n in range(1, count + 1)
        ]
        return Metered(drafts, {"input_tokens": len(brief) / 4, "output_tokens": 200 * count})

    def review(self, brief: str, drafts: list[Draft]) -> Metered[list[Verdict]]:
        return Metered([Verdict("pass", [], None) for _ in drafts], {"input_tokens": 100})


class _Item(BaseModel):
    title: str
    focus: str
    document: str
    question: str
    options: list[str]
    answer: int
    explanation: str

    def draft(self, slug: str) -> Draft:
        return Draft(
            slug,
            self.focus,
            self.document,
            self.question,
            tuple(self.options),
            self.answer,
            self.explanation,
        )


class _Items(BaseModel):
    items: list[_Item]


class _Verdict(BaseModel):
    index: int
    verdict: Literal["pass", "fix", "reject"]
    issues: list[str]
    corrected: _Item | None


class _Review(BaseModel):
    verdicts: list[_Verdict]


@cache
def _instructions(name: str) -> str:
    return (PROMPTS / name).read_text()


class AzureItemWriter:
    def __init__(self, client: openai.OpenAI, deployment: str) -> None:
        self._client = client
        self.model = deployment
        prompts = _instructions("write_items.md") + _instructions("review_items.md")
        self.fingerprint = hashlib.sha256(prompts.encode()).hexdigest()[:16]

    def write(self, brief: str, count: int, avoid: list[str]) -> Metered[list[Draft]]:
        existing = "\n".join(avoid) or "(none)"
        prompt = (
            f"<brief>\n{brief}\n</brief>\n\nWrite {count} items.\n\n"
            f"Existing items, by slug; do not repeat their situations:\n{existing}"
        )
        output, units = self._parse("write_items.md", prompt, _Items)
        return Metered([item.draft(item.title) for item in output.items], units)

    def review(self, brief: str, drafts: list[Draft]) -> Metered[list[Verdict]]:
        listed = "\n\n".join(_shown(i, d) for i, d in enumerate(drafts))
        prompt = f"<brief>\n{brief}\n</brief>\n\n<items>\n{listed}\n</items>"
        output, units = self._parse("review_items.md", prompt, _Review)
        by_index = {v.index: v for v in output.verdicts}
        verdicts = [
            Verdict(v.verdict, v.issues, v.corrected.draft("") if v.corrected else None)
            if (v := by_index.get(i))
            else Verdict("reject", ["the reviewer skipped this item"], None)
            for i in range(len(drafts))
        ]
        return Metered(verdicts, units)

    def _parse[T: BaseModel](
        self, prompt_file: str, prompt: str, schema: type[T]
    ) -> tuple[T, Units]:
        try:
            response = self._client.responses.parse(
                model=self.model,
                instructions=_instructions(prompt_file),
                input=prompt,
                text_format=schema,
                reasoning={"effort": "medium"},
                max_output_tokens=MAX_OUTPUT_TOKENS,
            )
        except openai.APIError as exc:
            raise ProviderUnavailableError(str(exc)) from exc
        if response.output_parsed is None or response.usage is None:
            raise ProviderUnavailableError("The item writer returned no structured output")
        return response.output_parsed, _units(response.usage)


def _units(usage: ResponseUsage) -> Units:
    cached = usage.input_tokens_details.cached_tokens
    return {
        "input_tokens": usage.input_tokens - cached,
        "cached_input_tokens": cached,
        "output_tokens": usage.output_tokens,
    }


def _shown(index: int, draft: Draft) -> str:
    options = "\n".join(f"  {n}. {option}" for n, option in enumerate(draft.options))
    return (
        f"[{index}] focus: {draft.focus}\ndocument: {draft.document}\n"
        f"question: {draft.prompt}\noptions:\n{options}\nanswer: {draft.answer}\n"
        f"explanation: {draft.explanation}"
    )
