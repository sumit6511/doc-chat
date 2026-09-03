"""Retrieval: question -> query embedding -> Atlas $vectorSearch -> ranked chunks.

This is the only consumer of ChunkRepository.vector_search. It never
downloads the full chunk collection and computes similarity in Python — the
similarity ranking happens inside MongoDB Atlas.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from bson import ObjectId

from app.db.repositories.chunks import ChunkRepository
from app.rag.embeddings import EmbeddingProvider

logger = logging.getLogger("docchat.retrieval")


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    content: str
    similarity_score: float


class RetrievalService:
    def __init__(self, chunk_repository: ChunkRepository, embedding_provider: EmbeddingProvider):
        self._chunks = chunk_repository
        self._embeddings = embedding_provider

    async def retrieve(
        self,
        question: str,
        *,
        top_k: int,
        num_candidates: int,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        query_vector = await self._embeddings.embed_query(question)

        object_ids = [ObjectId(doc_id) for doc_id in document_ids] if document_ids else None

        hits = await self._chunks.vector_search(
            query_vector,
            top_k=top_k,
            num_candidates=num_candidates,
            document_ids=object_ids,
        )

        results = [
            RetrievedChunk(
                chunk_id=str(hit["_id"]),
                document_id=str(hit["document_id"]),
                filename=hit.get("metadata", {}).get("filename", "Unknown document"),
                page_number=hit["page_number"],
                content=hit["content"],
                similarity_score=float(hit["score"]),
            )
            for hit in hits
        ]

        logger.info(
            "vector_search_executed candidates=%d top_k=%d results=%d",
            num_candidates,
            top_k,
            len(results),
        )
        return results

    @staticmethod
    def filter_by_relevance(
        chunks: list[RetrievedChunk], min_score: float
    ) -> list[RetrievedChunk]:
        return [chunk for chunk in chunks if chunk.similarity_score >= min_score]
