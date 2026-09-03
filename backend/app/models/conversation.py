from __future__ import annotations

from datetime import datetime, timezone

from pydantic import Field

from app.models.common import MongoBaseModel, PyObjectId


class Conversation(MongoBaseModel):
    title: str
    document_ids: list[PyObjectId] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
