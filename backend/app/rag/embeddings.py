"""Embedding generation, behind a provider abstraction.

Nothing outside this module imports `sentence_transformers` directly — the
rest of the app only ever talks to `EmbeddingProvider`, so swapping in a
hosted embeddings API later (OpenAI, Cohere, Voyage, ...) means adding one
new provider class, not touching ingestion or retrieval code.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from app.logging_config import get_logger

logger = get_logger("docchat.embeddings")


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Vector length produced by this provider — must match the Atlas index."""

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Batch-embeds chunk texts for storage."""

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Embeds a single user question for retrieval."""


class LocalSentenceTransformerProvider(EmbeddingProvider):
    """Runs a `sentence-transformers` model locally (no network calls at query time)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self._model_name = model_name
        self._model = SentenceTransformer(model_name)
        self._dimensions = self._model.get_sentence_embedding_dimension()
        logger.info("embedding_model_loaded", model=model_name, dimensions=self._dimensions)

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await asyncio.to_thread(self._encode, texts)

    async def embed_query(self, text: str) -> list[float]:
        vectors = await asyncio.to_thread(self._encode, [text])
        return vectors[0]

    def _encode(self, texts: list[str]) -> list[list[float]]:
        # normalize_embeddings=True => unit vectors, so cosine similarity in
        # Atlas Vector Search behaves consistently.
        embeddings = self._model.encode(
            texts, batch_size=32, normalize_embeddings=True, convert_to_numpy=True
        )
        return embeddings.tolist()
