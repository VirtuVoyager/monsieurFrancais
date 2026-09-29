import hashlib
import math
import re
import unicodedata
from typing import Protocol

import openai

from app.domain.cost import Metered
from app.llm.grader import ProviderUnavailableError
from app.models.knowledge import EMBEDDING_DIMENSIONS

Vector = list[float]


class Embedder(Protocol):
    model: str

    def embed(self, texts: list[str]) -> Metered[list[Vector]]: ...


class FakeEmbedder:
    """Hashed bag of words: texts sharing words point the same way, which is enough for tests."""

    model = "fake-embedding"

    def embed(self, texts: list[str]) -> Metered[list[Vector]]:
        vectors = [self._vector(text) for text in texts]
        return Metered(vectors, {"input_tokens": sum(len(t) for t in texts) / 4})

    @staticmethod
    def _vector(text: str) -> Vector:
        plain = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
        vector = [0.0] * EMBEDDING_DIMENSIONS
        for word in re.findall(r"[a-z]{3,}", plain):
            digest = hashlib.sha1(word.encode()).digest()
            vector[int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]


class AzureEmbedder:
    def __init__(self, client: openai.OpenAI, deployment: str) -> None:
        self._client = client
        self.model = deployment

    def embed(self, texts: list[str]) -> Metered[list[Vector]]:
        try:
            response = self._client.embeddings.create(
                model=self.model, input=texts, dimensions=EMBEDDING_DIMENSIONS
            )
        except openai.APIError as exc:
            raise ProviderUnavailableError(str(exc)) from exc
        vectors = [item.embedding for item in sorted(response.data, key=lambda d: d.index)]
        return Metered(vectors, {"input_tokens": response.usage.prompt_tokens})
