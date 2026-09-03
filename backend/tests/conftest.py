"""Shared test fixtures.

Unit tests never touch a real MongoDB Atlas cluster, a real sentence-
transformers model, or a real Ollama instance. `mongomock-motor` stands in
for MongoDB's CRUD API (list/insert/update/delete) in API-layer tests; the
Atlas-only `$vectorSearch` aggregation stage is exercised indirectly by
overriding the RAG pipeline / retrieval layer with fakes instead, since
mongomock cannot execute Atlas Search stages.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import pytest
import pytest_asyncio
from bson import ObjectId
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.api import deps
from app.db.client import get_database, get_database_or_none
from app.llm.base import LLMProvider
from app.main import app as fastapi_app
from app.rag.embeddings import EmbeddingProvider
from app.rag.pipeline import DebugChunk, RAGResult, StreamDelta, StreamStart
from app.rag.retrieval import RetrievedChunk
from app.services.file_storage import FileStorage


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic pseudo-embeddings — same text always yields the same vector."""

    def __init__(self, dimensions: int = 8):
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    def _vector(self, text: str) -> list[float]:
        seed = sum(ord(c) for c in text) or 1
        return [((seed * (i + 1)) % 97) / 97 for i in range(self._dimensions)]


class FakeLLMProvider(LLMProvider):
    def __init__(self, response: str = "This is a grounded answer based on the documents."):
        self.response = response
        self.calls: list[dict] = []

    async def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        return self.response

    async def generate_stream(self, *, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        words = self.response.split(" ")
        for i, word in enumerate(words):
            yield (" " if i > 0 else "") + word

    async def is_available(self) -> bool:
        return True


class FakeFileStorage(FileStorage):
    def __init__(self):
        self._store: dict[str, bytes] = {}

    async def save(self, storage_filename: str, content: bytes) -> str:
        self._store[storage_filename] = content
        return storage_filename

    async def get(self, storage_path: str) -> bytes:
        return self._store[storage_path]

    async def delete(self, storage_path: str) -> None:
        self._store.pop(storage_path, None)


@dataclass
class FakeRAGPipeline:
    """Stands in for RAGPipeline in API tests so message creation never needs
    a real Atlas $vectorSearch or a real LLM."""

    result: RAGResult | None = None
    calls: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if self.result is None:
            self.result = _default_rag_result()

    async def answer(self, question, *, document_ids=None, history=None) -> RAGResult:
        self.calls.append({"question": question, "document_ids": document_ids, "history": history})
        return self.result

    async def answer_stream(
        self, question, *, document_ids=None, history=None
    ) -> AsyncIterator[StreamStart | StreamDelta]:
        self.calls.append({"question": question, "document_ids": document_ids, "history": history})
        yield StreamStart(sources=self.result.sources, debug_chunks=self.result.debug_chunks)
        words = self.result.answer.split(" ")
        for i, word in enumerate(words):
            yield StreamDelta(text=(" " if i > 0 else "") + word)


def _default_rag_result() -> RAGResult:
    chunk = RetrievedChunk(
        chunk_id=str(ObjectId()),
        document_id=str(ObjectId()),
        filename="sample.pdf",
        page_number=1,
        content="Sample retrieved content.",
        similarity_score=0.9,
    )
    return RAGResult(
        answer="This is a grounded answer based on the documents.",
        sources=[chunk],
        debug_chunks=[DebugChunk(chunk=chunk, used=True)],
    )


@pytest.fixture
def fake_db():
    client = AsyncMongoMockClient()
    return client["docchat_test"]


@pytest.fixture
def fake_embedding_provider():
    return FakeEmbeddingProvider()


@pytest.fixture
def fake_llm_provider():
    return FakeLLMProvider()


@pytest.fixture
def fake_file_storage():
    return FakeFileStorage()


@pytest.fixture
def fake_rag_pipeline():
    return FakeRAGPipeline()


@pytest_asyncio.fixture
async def api_client(fake_db, fake_embedding_provider, fake_llm_provider, fake_file_storage, fake_rag_pipeline):
    fastapi_app.dependency_overrides[get_database] = lambda: fake_db
    fastapi_app.dependency_overrides[get_database_or_none] = lambda: fake_db
    fastapi_app.dependency_overrides[deps.get_embedding_provider] = lambda: fake_embedding_provider
    fastapi_app.dependency_overrides[deps.get_llm_provider] = lambda: fake_llm_provider
    fastapi_app.dependency_overrides[deps.get_file_storage] = lambda: fake_file_storage
    fastapi_app.dependency_overrides[deps.get_rag_pipeline] = lambda: fake_rag_pipeline

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    fastapi_app.dependency_overrides.clear()


def make_minimal_pdf_bytes(text: str = "Hello DocChat", pages: int = 1) -> bytes:
    """Builds a tiny real PDF in-memory via PyMuPDF, for upload/extraction tests."""
    import fitz

    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"{text} (page {i + 1})")
    content = doc.tobytes()
    doc.close()
    return content
