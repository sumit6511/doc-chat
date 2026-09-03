"""PDF -> pages -> chunks -> embeddings -> MongoDB.

    PDF
     v
    page iteration        (PyMuPDF)
     v
    text extraction
     v
    whitespace normalization + paragraph-aware chunking   (rag/chunker.py)
     v
    batch embedding generation                            (rag/embeddings.py)
     v
    MongoDB insertion                                      (ChunkRepository)

Runs as a FastAPI background task (see api/documents.py) so the upload
request returns immediately. A failure anywhere in the pipeline marks the
document FAILED with a user-safe error_message instead of raising into the
background task runner.
"""

from __future__ import annotations

import logging

import fitz
from bson import ObjectId

from app.db.repositories.chunks import ChunkRepository
from app.db.repositories.documents import DocumentRepository
from app.errors import CorruptedFileError
from app.models.chunk import ChunkMetadata, DocumentChunk
from app.models.document import DocumentStatus
from app.rag.chunker import chunk_text
from app.rag.embeddings import EmbeddingProvider

logger = logging.getLogger("docchat.ingestion")


def open_pdf(pdf_bytes: bytes) -> fitz.Document:
    """Opens and sanity-checks a PDF. Raises CorruptedFileError if unreadable."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:  # PyMuPDF raises its own exception types
        raise CorruptedFileError("The uploaded file is not a valid or readable PDF.") from exc
    if doc.page_count == 0:
        doc.close()
        raise CorruptedFileError("The PDF has no pages.")
    return doc


def extract_pages_text(pdf_bytes: bytes) -> list[str]:
    """Returns one text string per page, in page order (1-indexed by caller)."""
    doc = open_pdf(pdf_bytes)
    try:
        return [page.get_text("text") for page in doc]
    finally:
        doc.close()


class IngestionService:
    def __init__(
        self,
        document_repository: DocumentRepository,
        chunk_repository: ChunkRepository,
        embedding_provider: EmbeddingProvider,
        *,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
    ):
        self._documents = document_repository
        self._chunks = chunk_repository
        self._embeddings = embedding_provider
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    async def process_document(self, document_id: ObjectId, pdf_bytes: bytes) -> None:
        document = await self._documents.get_by_id(document_id)
        if document is None:
            logger.warning("ingestion_skipped_missing_document document_id=%s", document_id)
            return

        logger.info("document_processing_started document_id=%s", document_id)
        try:
            pages = extract_pages_text(pdf_bytes)
            logger.info("page_extraction_completed document_id=%s pages=%d", document_id, len(pages))

            chunk_records: list[tuple[int, str]] = []
            for page_number, page_text in enumerate(pages, start=1):
                for text_chunk in chunk_text(page_text, self._chunk_size, self._chunk_overlap):
                    chunk_records.append((page_number, text_chunk.content))

            if not chunk_records:
                await self._documents.update_status(
                    document_id,
                    DocumentStatus.FAILED,
                    error_message="No extractable text was found in this PDF. It may be a "
                    "scanned/image-only document (OCR is not yet supported).",
                )
                logger.warning("document_processing_no_text document_id=%s", document_id)
                return

            texts = [content for _, content in chunk_records]
            embeddings = await self._embeddings.embed_documents(texts)
            logger.info(
                "embedding_generation_completed document_id=%s chunks=%d", document_id, len(texts)
            )

            chunks = [
                DocumentChunk(
                    document_id=document_id,
                    content=text,
                    page_number=page_number,
                    chunk_index=i,
                    embedding=embedding,
                    metadata=ChunkMetadata(filename=document.original_filename),
                )
                for i, ((page_number, text), embedding) in enumerate(zip(chunk_records, embeddings))
            ]

            await self._chunks.insert_many(chunks)
            logger.info("chunks_indexed document_id=%s chunks=%d", document_id, len(chunks))

            await self._documents.update_processing_result(
                document_id, page_count=len(pages), chunk_count=len(chunks)
            )
            logger.info("document_processing_completed document_id=%s", document_id)

        except Exception:
            logger.exception("document_processing_failed document_id=%s", document_id)
            await self._documents.update_status(
                document_id,
                DocumentStatus.FAILED,
                error_message="Processing failed. The file may be corrupted or in an "
                "unsupported format.",
            )
