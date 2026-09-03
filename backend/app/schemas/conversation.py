from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ConversationCreateRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)
    title: str | None = None


class ConversationUpdateRequest(BaseModel):
    title: str | None = None
    document_ids: list[str] | None = None


class ConversationResponse(BaseModel):
    id: str
    title: str
    document_ids: list[str]
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int
