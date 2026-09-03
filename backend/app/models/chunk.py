from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.models.common import MongoBaseModel, PyObjectId


class ChunkMetadata(BaseModel):
    """Loose bag of extra context embedded alongside a chunk (e.g. source filename).

    Deliberately a plain BaseModel, not MongoBaseModel — it's an embedded
    sub-document, not a top-level Mongo document, so it must not pick up
    MongoBaseModel's `id` field (which would persist as a stray `null`).
    """

    filename: str


class DocumentChunk(MongoBaseModel):
    document_id: PyObjectId
    content: str
    page_number: int
    chunk_index: int
    embedding: list[float] = Field(default_factory=list)
    metadata: ChunkMetadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
