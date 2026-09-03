from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import Field

from app.models.common import MongoBaseModel


class DocumentStatus(StrEnum):
    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class Document(MongoBaseModel):
    filename: str
    original_filename: str
    storage_path: str
    file_size: int
    page_count: int | None = None
    status: DocumentStatus = DocumentStatus.UPLOADING
    error_message: str | None = None
    chunk_count: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
