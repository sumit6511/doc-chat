from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.document import DocumentStatus


class DocumentResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_size: int
    page_count: int | None
    chunk_count: int | None
    status: DocumentStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
