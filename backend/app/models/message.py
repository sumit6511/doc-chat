from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.common import MongoBaseModel, PyObjectId


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class MessageSource(BaseModel):
    """An embedded citation on an assistant message — not a top-level Mongo
    document, so (like ChunkMetadata) this must stay a plain BaseModel rather
    than MongoBaseModel to avoid picking up a spurious `id` field."""

    chunk_id: PyObjectId
    document_id: PyObjectId
    filename: str
    page_number: int
    similarity_score: float


class Message(MongoBaseModel):
    conversation_id: PyObjectId
    role: MessageRole
    content: str
    sources: list[MessageSource] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
