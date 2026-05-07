"""
Embedding service — abstract interface + OpenAI implementation.
Ready to be extended with Gemini or Anthropic embeddings.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ─── Abstract interface ───────────────────────────────────────────────────────

class EmbeddingProvider(ABC):
    """Abstract interface for embedding providers."""

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts and return their vectors."""
        ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the number of dimensions in the embedding vectors."""
        ...


# ─── OpenAI Implementation ───────────────────────────────────────────────────

class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embeddings via openai SDK."""

    _BATCH_SIZE = 100  # OpenAI allows up to 2048 per request, but let's keep safe

    def __init__(
        self,
        api_key: str = settings.openai_api_key,
        model: str = settings.embedding_model,
    ) -> None:
        from openai import OpenAI

        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Please configure it in your .env file."
            )
        self._client = OpenAI(api_key=api_key)
        self._model = model
        logger.info(f"OpenAI embedding provider initialized (model={model})")

    @property
    def dimensions(self) -> int:
        # text-embedding-3-small = 1536, text-embedding-3-large = 3072
        if "large" in self._model:
            return 3072
        return 1536

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        all_vectors: list[list[float]] = []
        for i in range(0, len(texts), self._BATCH_SIZE):
            batch = texts[i : i + self._BATCH_SIZE]
            response = self._client.embeddings.create(model=self._model, input=batch)
            batch_vectors = [item.embedding for item in response.data]
            all_vectors.extend(batch_vectors)
            logger.debug(f"Embedded batch {i//self._BATCH_SIZE + 1}: {len(batch)} texts")
        return all_vectors

    def embed_query(self, text: str) -> list[float]:
        response = self._client.embeddings.create(model=self._model, input=[text])
        return response.data[0].embedding


# ─── Provider factory ─────────────────────────────────────────────────────────

def get_embedding_provider() -> EmbeddingProvider:
    """Factory — returns the configured embedding provider."""
    # Future: check settings for Gemini, Anthropic, local model, etc.
    return OpenAIEmbeddingProvider()
