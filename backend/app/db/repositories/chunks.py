"""Chunk persistence and the Atlas Vector Search retrieval path.

`vector_search` is the one place in the codebase allowed to run a
`$vectorSearch` aggregation — everything upstream (RetrievalService) treats it
as an opaque "give me the top-K relevant chunks" call. The similarity
computation itself happens inside MongoDB Atlas, not in Python.
"""

from __future__ import annotations

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import OperationFailure

from app.config import get_settings
from app.errors import VectorSearchError
from app.logging_config import get_logger
from app.models.chunk import DocumentChunk

logger = get_logger("docchat.retrieval")


class ChunkRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._collection = db.document_chunks

    async def insert_many(self, chunks: list[DocumentChunk]) -> int:
        if not chunks:
            return 0
        result = await self._collection.insert_many([c.to_mongo() for c in chunks])
        return len(result.inserted_ids)

    async def delete_by_document_id(self, document_id: ObjectId) -> int:
        result = await self._collection.delete_many({"document_id": document_id})
        return result.deleted_count

    async def count_by_document_id(self, document_id: ObjectId) -> int:
        return await self._collection.count_documents({"document_id": document_id})

    async def vector_search(
        self,
        query_vector: list[float],
        *,
        top_k: int,
        num_candidates: int,
        document_ids: list[ObjectId] | None = None,
    ) -> list[dict]:
        """Runs a $vectorSearch aggregation against Atlas and returns raw hits.

        Each hit dict has: _id, document_id, content, page_number, chunk_index,
        metadata, score (cosine similarity in [-1, 1], via $meta: vectorSearchScore).
        """
        settings = get_settings()

        vector_search_stage: dict = {
            "index": settings.vector_index_name,
            "path": "embedding",
            "queryVector": query_vector,
            "numCandidates": num_candidates,
            "limit": top_k,
        }
        if document_ids:
            # Requires the `document_id` field to be configured as a `filter`
            # type in the Atlas Vector Search index definition (see README).
            vector_search_stage["filter"] = {"document_id": {"$in": document_ids}}

        pipeline = [
            {"$vectorSearch": vector_search_stage},
            {
                "$project": {
                    "_id": 1,
                    "document_id": 1,
                    "content": 1,
                    "page_number": 1,
                    "chunk_index": 1,
                    "metadata": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        try:
            cursor = self._collection.aggregate(pipeline)
            return [doc async for doc in cursor]
        except OperationFailure as exc:
            logger.error("vector_search_failed", exc_info=True, reason=exc.details)
            raise VectorSearchError(
                "Vector search is not available. Verify the Atlas Vector Search "
                "index has been created (see README)."
            ) from exc
