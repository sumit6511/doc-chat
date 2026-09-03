import pytest
from bson import ObjectId

from app.rag.retrieval import RetrievalService, RetrievedChunk
from tests.conftest import FakeEmbeddingProvider


class FakeChunkRepository:
    """Stands in for ChunkRepository so retrieval logic is tested without Atlas."""

    def __init__(self, hits: list[dict]):
        self.hits = hits
        self.last_call: dict | None = None

    async def vector_search(self, query_vector, *, top_k, num_candidates, document_ids=None):
        self.last_call = {
            "query_vector": query_vector,
            "top_k": top_k,
            "num_candidates": num_candidates,
            "document_ids": document_ids,
        }
        return self.hits


def _hit(score: float, page: int = 1, filename: str = "notes.pdf") -> dict:
    return {
        "_id": ObjectId(),
        "document_id": ObjectId(),
        "content": "Some retrieved chunk content.",
        "page_number": page,
        "chunk_index": 0,
        "metadata": {"filename": filename},
        "score": score,
    }


@pytest.mark.asyncio
class TestRetrievalService:
    async def test_retrieve_embeds_the_query(self):
        repo = FakeChunkRepository([_hit(0.9)])
        embeddings = FakeEmbeddingProvider(dimensions=4)
        service = RetrievalService(repo, embeddings)

        await service.retrieve("What is RPC?", top_k=5, num_candidates=50)

        expected_vector = await embeddings.embed_query("What is RPC?")
        assert repo.last_call["query_vector"] == expected_vector

    async def test_retrieve_passes_top_k_and_num_candidates(self):
        repo = FakeChunkRepository([_hit(0.9)])
        service = RetrievalService(repo, FakeEmbeddingProvider())

        await service.retrieve("question", top_k=3, num_candidates=40)

        assert repo.last_call["top_k"] == 3
        assert repo.last_call["num_candidates"] == 40

    async def test_retrieve_converts_document_id_strings_to_object_ids(self):
        repo = FakeChunkRepository([_hit(0.9)])
        service = RetrievalService(repo, FakeEmbeddingProvider())
        doc_id = str(ObjectId())

        await service.retrieve("question", top_k=5, num_candidates=50, document_ids=[doc_id])

        assert repo.last_call["document_ids"] == [ObjectId(doc_id)]

    async def test_retrieve_with_no_document_filter_passes_none(self):
        repo = FakeChunkRepository([_hit(0.9)])
        service = RetrievalService(repo, FakeEmbeddingProvider())

        await service.retrieve("question", top_k=5, num_candidates=50)

        assert repo.last_call["document_ids"] is None

    async def test_retrieve_maps_hits_to_retrieved_chunks(self):
        hit = _hit(0.87, page=42, filename="Distributed Systems.pdf")
        repo = FakeChunkRepository([hit])
        service = RetrievalService(repo, FakeEmbeddingProvider())

        results = await service.retrieve("question", top_k=5, num_candidates=50)

        assert len(results) == 1
        chunk = results[0]
        assert isinstance(chunk, RetrievedChunk)
        assert chunk.page_number == 42
        assert chunk.filename == "Distributed Systems.pdf"
        assert chunk.similarity_score == pytest.approx(0.87)
        assert chunk.chunk_id == str(hit["_id"])


class TestRelevanceFiltering:
    def test_filters_out_chunks_below_threshold(self):
        chunks = [
            RetrievedChunk("1", "d1", "a.pdf", 1, "content a", 0.9),
            RetrievedChunk("2", "d1", "a.pdf", 2, "content b", 0.3),
        ]
        filtered = RetrievalService.filter_by_relevance(chunks, min_score=0.5)
        assert [c.chunk_id for c in filtered] == ["1"]

    def test_keeps_all_when_all_above_threshold(self):
        chunks = [
            RetrievedChunk("1", "d1", "a.pdf", 1, "content a", 0.9),
            RetrievedChunk("2", "d1", "a.pdf", 2, "content b", 0.6),
        ]
        filtered = RetrievalService.filter_by_relevance(chunks, min_score=0.5)
        assert len(filtered) == 2

    def test_empty_input_returns_empty(self):
        assert RetrievalService.filter_by_relevance([], min_score=0.5) == []
