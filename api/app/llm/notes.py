from functools import cache
from pathlib import Path
from typing import Literal, Protocol

import openai
from pydantic import BaseModel

from app.domain.cost import Metered, Units
from app.domain.notes import NoteEntry, capped, table_entries
from app.llm.grader import ProviderUnavailableError


class NoteExtractor(Protocol):
    model: str

    def extract(self, title: str, markdown: str) -> Metered[list[NoteEntry]]: ...


class FakeNoteExtractor:
    model = "fake-text"

    def extract(self, title: str, markdown: str) -> Metered[list[NoteEntry]]:
        return Metered(table_entries(markdown), {"input_tokens": len(markdown) / 4})


class _Word(BaseModel):
    french: str
    gender: Literal["m", "f", ""]
    english: str
    example_french: str


class _Sentence(BaseModel):
    french: str
    english: str


class _Grammar(BaseModel):
    title: str
    explanation: str


class _Extraction(BaseModel):
    words: list[_Word]
    sentences: list[_Sentence]
    grammar: list[_Grammar]


@cache
def _instructions() -> str:
    return (Path(__file__).parent / "prompts" / "extract_notes.md").read_text()


class AzureNoteExtractor:
    def __init__(self, client: openai.OpenAI, deployment: str) -> None:
        self._client = client
        self.model = deployment

    def extract(self, title: str, markdown: str) -> Metered[list[NoteEntry]]:
        try:
            response = self._client.responses.parse(
                model=self.model,
                instructions=_instructions(),
                input=f"Title: {title}\n\n<notes>\n{markdown}\n</notes>",
                text_format=_Extraction,
                reasoning={"effort": "low"},
            )
        except openai.APIError as exc:
            raise ProviderUnavailableError(str(exc)) from exc
        output = response.output_parsed
        if output is None or response.usage is None:
            raise ProviderUnavailableError("The extractor returned no structured output")
        usage = response.usage
        cached = usage.input_tokens_details.cached_tokens
        units: Units = {
            "input_tokens": usage.input_tokens - cached,
            "cached_input_tokens": cached,
            "output_tokens": usage.output_tokens,
        }
        entries = [
            NoteEntry("word", w.french, w.english, w.gender or None, w.example_french)
            for w in output.words
        ]
        entries += [NoteEntry("sentence", s.french, s.english) for s in output.sentences]
        entries += [NoteEntry("grammar", g.title, detail=g.explanation) for g in output.grammar]
        return Metered(capped(entries), units)
