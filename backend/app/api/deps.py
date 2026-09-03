"""FastAPI dependency wiring.

Repositories are cheap and are constructed per-request from the one shared
Motor client. The embedding model, LLM client, and file storage are
expensive/stateful singletons created once at startup and stashed on
`app.state` (see app/main.py's lifespan) — request-scoped dependencies here
just retrieve them.
"""

from __future__ import annotations

from fastapi import Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import Settings, get_settings
from app.db.client import get_database
from app.db.repositories.chunks import ChunkRepository
from app.db.repositories.conversations import ConversationRepository
from app.db.repositories.documents import DocumentRepository
from app.db.repositories.messages import MessageRepository
from app.llm.base import LLMProvider
from app.rag.context import ContextBuilder
from app.rag.embeddings import EmbeddingProvider
from app.rag.pipeline import RAGPipeline
from app.rag.retrieval import RetrievalService
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.services.file_storage import FileStorage
from app.services.ingestion_service import IngestionService


def get_document_repository(db: AsyncIOMotorDatabase = Depends(get_database)) -> DocumentRepository:
    return DocumentRepository(db)


def get_chunk_repository(db: AsyncIOMotorDatabase = Depends(get_database)) -> ChunkRepository:
    return ChunkRepository(db)


def get_conversation_repository(
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> ConversationRepository:
    return ConversationRepository(db)


def get_message_repository(db: AsyncIOMotorDatabase = Depends(get_database)) -> MessageRepository:
    return MessageRepository(db)


def get_file_storage(request: Request) -> FileStorage:
    return request.app.state.file_storage


def get_embedding_provider(request: Request) -> EmbeddingProvider:
    return request.app.state.embedding_provider


def get_llm_provider(request: Request) -> LLMProvider:
    return request.app.state.llm_provider


def get_document_service(
    document_repo: DocumentRepository = Depends(get_document_repository),
    chunk_repo: ChunkRepository = Depends(get_chunk_repository),
    file_storage: FileStorage = Depends(get_file_storage),
    settings: Settings = Depends(get_settings),
) -> DocumentService:
    return DocumentService(
        document_repo, chunk_repo, file_storage, max_file_size_bytes=settings.max_file_size_bytes
    )


def get_ingestion_service(
    document_repo: DocumentRepository = Depends(get_document_repository),
    chunk_repo: ChunkRepository = Depends(get_chunk_repository),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    settings: Settings = Depends(get_settings),
) -> IngestionService:
    return IngestionService(
        document_repo,
        chunk_repo,
        embedding_provider,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )


def get_rag_pipeline(
    chunk_repo: ChunkRepository = Depends(get_chunk_repository),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    llm_provider: LLMProvider = Depends(get_llm_provider),
    settings: Settings = Depends(get_settings),
) -> RAGPipeline:
    retrieval_service = RetrievalService(chunk_repo, embedding_provider)
    context_builder = ContextBuilder()
    return RAGPipeline(
        retrieval_service,
        context_builder,
        llm_provider,
        top_k=settings.top_k,
        num_candidates=settings.num_candidates,
        min_relevance_score=settings.min_relevance_score,
    )


def get_chat_service(
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
    message_repo: MessageRepository = Depends(get_message_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline),
    settings: Settings = Depends(get_settings),
) -> ChatService:
    return ChatService(
        conversation_repo,
        message_repo,
        document_repo,
        rag_pipeline,
        max_history_messages=settings.max_history_messages,
    )
