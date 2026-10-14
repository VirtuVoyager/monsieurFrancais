from functools import cache
from pathlib import Path
from typing import Protocol

import openai
from pydantic import BaseModel

from app.domain.cost import Metered, Units
from app.domain.glossary import Gloss
from app.llm.grader import ProviderUnavailableError


class Glosser(Protocol):
    model: str

    def gloss(self, text: str, forms: list[str], phrases: bool) -> Metered[list[Gloss]]: ...


# Enough of the A1 core to make the hover usable offline; everything else stays untranslated.
_OFFLINE = {
    "je": ("je", "I"),
    "j'": ("je", "I"),
    "tu": ("tu", "you"),
    "il": ("il", "he / it"),
    "elle": ("elle", "she / it"),
    "nous": ("nous", "we"),
    "vous": ("vous", "you"),
    "suis": ("être", "(I) am"),
    "es": ("être", "(you) are"),
    "est": ("être", "is"),
    "sommes": ("être", "(we) are"),
    "êtes": ("être", "(you) are"),
    "sont": ("être", "(they) are"),
    "ai": ("avoir", "(I) have"),
    "as": ("avoir", "(you) have"),
    "a": ("avoir", "has"),
    "avons": ("avoir", "(we) have"),
    "avez": ("avoir", "(you) have"),
    "ont": ("avoir", "(they) have"),
    "et": ("et", "and"),
    "mais": ("mais", "but"),
    "le": ("le", "the"),
    "la": ("la", "the"),
    "les": ("les", "the"),
    "un": ("un", "a"),
    "une": ("une", "a"),
    "de": ("de", "of / from"),
    "ans": ("an", "years"),
    "famille": ("la famille", "family"),
    "il y a": ("il y a", "there is / there are"),
    "parce que": ("parce que", "because"),
}


class FakeGlosser:
    model = "fake-text"

    def gloss(self, text: str, forms: list[str], phrases: bool) -> Metered[list[Gloss]]:
        wanted = [*forms, *(f for f in _OFFLINE if " " in f and phrases and f in text.lower())]
        glosses = [Gloss(f, *_OFFLINE[f]) for f in wanted if f in _OFFLINE]
        return Metered(glosses, {"input_tokens": len(text) / 4, "output_tokens": 10 * len(forms)})


class _Entry(BaseModel):
    french: str
    lemma: str
    english: str


class _Glossary(BaseModel):
    entries: list[_Entry]


@cache
def _instructions() -> str:
    return (Path(__file__).parent / "prompts" / "gloss.md").read_text()


class AzureGlosser:
    def __init__(self, client: openai.OpenAI, deployment: str) -> None:
        self._client = client
        self.model = deployment

    def gloss(self, text: str, forms: list[str], phrases: bool) -> Metered[list[Gloss]]:
        # The text comes first so every batch of the same module shares a cached prefix.
        ask = "Also return the fixed phrases." if phrases else "Do not return phrases."
        prompt = f"<text>\n{text}\n</text>\n\n{ask}\nForms:\n" + "\n".join(forms)
        try:
            response = self._client.responses.parse(
                model=self.model,
                instructions=_instructions(),
                input=prompt,
                text_format=_Glossary,
                reasoning={"effort": "low"},
            )
        except openai.APIError as exc:
            raise ProviderUnavailableError(str(exc)) from exc
        output = response.output_parsed
        if output is None or response.usage is None:
            raise ProviderUnavailableError("The glosser returned no structured output")
        usage = response.usage
        cached = usage.input_tokens_details.cached_tokens
        units: Units = {
            "input_tokens": usage.input_tokens - cached,
            "cached_input_tokens": cached,
            "output_tokens": usage.output_tokens,
        }
        return Metered([Gloss(e.french, e.lemma, e.english) for e in output.entries], units)
