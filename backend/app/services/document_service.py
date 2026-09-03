"""Upload validation, document lifecycle, and deletion."""

from __future__ import annotations

import logging

from bson import ObjectId

from app.db.repositories.chunks import ChunkRepository
from app.db.repositories.documents import DocumentRepository
from app.errors import FileTooLargeError, InvalidFileTypeError, NotFoundError
from app.models.document import Document, DocumentStatus
from app.services.file_storage import (
    FileStorage,
    generate_storage_filename,
    sanitize_display_filename,
)
from app.services.ingestion_service import open_pdf

logger = logging.getLogger("docchat.documents")


class DocumentService:
    def __init__(
        self,
        document_repository: DocumentRepository,
        chunk_repository: ChunkRepository,
        file_storage: FileStorage,
        *,
        max_file_size_bytes: int,
    ):
        self._documents = document_repository
        self._chunks = chunk_repository
        self._storage = file_storage
        self._max_file_size_bytes = max_file_size_bytes

    def validate_upload(self, filename: str, content_type: str | None, content: bytes) -> int:
        """Validates extension, declared MIME type, size, and real PDF readability.

        Returns the page count on success; raises a DocChatError otherwise.
        """
        if not filename.lower().endswith(".pdf"):
            raise InvalidFileTypeError("Only PDF files are supported.")

        if content_type and content_type not in ("application/pdf", "application/octet-stream"):
            raise InvalidFileTypeError("Only PDF files are supported.")

        if not content:
            raise InvalidFileTypeError("The uploaded file is empty.")

        if len(content) > self._max_file_size_bytes:
            limit_mb = self._max_file_size_bytes // (1024 * 1024)
            raise FileTooLargeError(f"File exceeds the {limit_mb} MB upload limit.")

        pdf_doc = open_pdf(content)  # raises CorruptedFileError if unreadable
        try:
            return pdf_doc.page_count
        finally:
            pdf_doc.close()

    async def create_document(
        self, original_filename: str, content_type: str | None, content: bytes
    ) -> Document:
        page_count = self.validate_upload(original_filename, content_type, content)

        display_filename = sanitize_display_filename(original_filename)
        storage_filename = generate_storage_filename(original_filename)
        storage_path = await self._storage.save(storage_filename, content)

        document = Document(
            filename=storage_filename,
            original_filename=display_filename,
            storage_path=storage_path,
            file_size=len(content),
            page_count=page_count,
            status=DocumentStatus.PROCESSING,
        )
        document = await self._documents.create(document)
        logger.info(
            "document_upload_started document_id=%s pages=%d size=%d",
            document.id,
            page_count,
            len(content),
        )
        return document

    async def get_document(self, document_id: ObjectId) -> Document:
        document = await self._documents.get_by_id(document_id)
        if document is None:
            raise NotFoundError("Document not found.")
        return document

    async def list_documents(self) -> list[Document]:
        return await self._documents.list_all()

    async def delete_document(self, document_id: ObjectId) -> None:
        document = await self._documents.get_by_id(document_id)
        if document is None:
            raise NotFoundError("Document not found.")

        await self._chunks.delete_by_document_id(document_id)
        await self._storage.delete(document.storage_path)
        await self._documents.delete(document_id)
        logger.info("document_deleted document_id=%s", document_id)

    async def read_file(self, document_id: ObjectId) -> tuple[bytes, str]:
        document = await self.get_document(document_id)
        content = await self._storage.get(document.storage_path)
        return content, document.original_filename
