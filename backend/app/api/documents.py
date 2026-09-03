from __future__ import annotations

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from fastapi.responses import Response

from app.api.deps import get_document_service, get_ingestion_service
from app.errors import NotFoundError
from app.models.document import Document
from app.schemas.document import DocumentListResponse, DocumentResponse
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/documents", tags=["documents"])


def _parse_object_id(raw_id: str) -> ObjectId:
    try:
        return ObjectId(raw_id)
    except (InvalidId, TypeError) as exc:
        raise NotFoundError("Document not found.") from exc


def _to_response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=str(document.id),
        filename=document.filename,
        original_filename=document.original_filename,
        file_size=document.file_size,
        page_count=document.page_count,
        chunk_count=document.chunk_count,
        status=document.status,
        error_message=document.error_message,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.get("", response_model=DocumentListResponse, summary="List uploaded documents")
async def list_documents(
    service: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    documents = await service.list_documents()
    return DocumentListResponse(documents=[_to_response(d) for d in documents], total=len(documents))


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=201,
    summary="Upload a PDF for ingestion",
    description=(
        "Validates and stores the PDF, creates a document record with status "
        "PROCESSING, and schedules text extraction/chunking/embedding as a "
        "background task. Poll GET /documents/{id} until status is READY or FAILED."
    ),
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service),
    ingestion: IngestionService = Depends(get_ingestion_service),
) -> DocumentResponse:
    content = await file.read()
    document = await service.create_document(
        file.filename or "document.pdf", file.content_type, content
    )
    background_tasks.add_task(ingestion.process_document, document.id, content)
    return _to_response(document)


@router.get("/{document_id}", response_model=DocumentResponse, summary="Get document status/metadata")
async def get_document(
    document_id: str, service: DocumentService = Depends(get_document_service)
) -> DocumentResponse:
    document = await service.get_document(_parse_object_id(document_id))
    return _to_response(document)


@router.get("/{document_id}/file", summary="Download/stream the original PDF for viewing")
async def get_document_file(
    document_id: str, service: DocumentService = Depends(get_document_service)
) -> Response:
    content, filename = await service.read_file(_parse_object_id(document_id))
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.delete(
    "/{document_id}", status_code=204, response_model=None, summary="Delete a document and its chunks"
)
async def delete_document(
    document_id: str, service: DocumentService = Depends(get_document_service)
) -> None:
    await service.delete_document(_parse_object_id(document_id))
