from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.message import MessageRole


class SourceSchema(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    similarity_score: float


class DebugRetrievedChunk(BaseModel):
    """Extra detail returned only when DEBUG_RAG=true, for demoing the pipeline."""

    filename: str
    page_number: int
    score: float
    used: bool


class MessageCreateRequest(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    sources: list[SourceSchema] = []
    debug_retrieved_chunks: list[DebugRetrievedChunk] | None = None
    created_at: datetime


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]
