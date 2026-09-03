import pytest

from app.rag.context import ContextBuilder
from app.rag.pipeline import RAGPipeline, StreamDelta, StreamStart
from app.rag.prompts import NO_CONTEXT_ANSWER, SYSTEM_PROMPT
from app.rag.retrieval import RetrievedChunk
from tests.conftest import FakeLLMProvider


def _chunk(chunk_id="c1", score=0.9, page=1, filename="notes.pdf", content="Some content."):
    return RetrievedChunk(chunk_id, "doc1", filename, page, content, score)


class FakeRetrievalService:
    def __init__(self, chunks: list[RetrievedChunk]):
        self.chunks = chunks
        self.last_call: dict | None = None

    async def retrieve(self, question, *, top_k, num_candidates, document_ids=None):
        self.last_call = {
            "question": question,
            "top_k": top_k,
            "num_candidates": num_candidates,
            "document_ids": document_ids,
        }
        return self.chunks


class TestContextBuilder:
    def test_formats_sources_with_document_page_and_content(self):
        chunks = [_chunk("c1", 0.9, page=42, filename="Distributed Systems.pdf", content="RPC allows...")]
        context, sources = ContextBuilder().build(chunks)

        assert "[Source 1]" in context
        assert "Document: Distributed Systems.pdf" in context
        assert "Page: 42" in context
        assert "RPC allows..." in context
        assert len(sources) == 1
        assert sources[0].chunk.chunk_id == "c1"

    def test_deduplicates_near_identical_chunks(self):
        chunks = [
            _chunk("c1", 0.9, content="Remote Procedure Call allows a client to invoke a remote procedure."),
            _chunk("c2", 0.85, content="Remote Procedure Call allows a client to invoke a remote procedure."),
        ]
        context, sources = ContextBuilder().build(chunks)
        assert len(sources) == 1

    def test_keeps_distinct_chunks(self):
        chunks = [
            _chunk("c1", 0.9, content="Content about RPC."),
            _chunk("c2", 0.85, content="Content about RMI, a completely different topic."),
        ]
        _, sources = ContextBuilder().build(chunks)
        assert len(sources) == 2

    def test_respects_max_context_chars(self):
        # Each chunk's content alone (~1000 chars) already exceeds the small
        # budget below, so the limit should cut this down to far fewer than
        # all 10 chunks — the first section is always kept even if it alone
        # exceeds the budget, so it isn't a hard cap.
        chunks = [_chunk(f"c{i}", 0.9, content=f"unique-{i} " + "word " * 200) for i in range(10)]
        context, sources = ContextBuilder(max_context_chars=500).build(chunks)
        assert len(sources) < len(chunks)
        full_length = sum(len(c.content) for c in chunks)
        assert len(context) < full_length

    def test_empty_chunks_returns_empty_context(self):
        context, sources = ContextBuilder().build([])
        assert context == ""
        assert sources == []


@pytest.mark.asyncio
class TestRAGPipeline:
    async def _pipeline(self, chunks, min_relevance_score=0.5, llm=None):
        retrieval = FakeRetrievalService(chunks)
        llm = llm or FakeLLMProvider()
        pipeline = RAGPipeline(
            retrieval,
            ContextBuilder(),
            llm,
            top_k=5,
            num_candidates=50,
            min_relevance_score=min_relevance_score,
        )
        return pipeline, retrieval, llm

    async def test_answer_includes_llm_response_and_sources(self):
        chunks = [_chunk("c1", 0.9, page=42, filename="Distributed Systems.pdf")]
        pipeline, _, llm = await self._pipeline(chunks)

        result = await pipeline.answer("What is RPC?")

        assert result.answer == llm.response
        assert len(result.sources) == 1
        assert result.sources[0].chunk_id == "c1"

    async def test_system_prompt_is_passed_to_llm_unmodified(self):
        pipeline, _, llm = await self._pipeline([_chunk("c1", 0.9)])
        await pipeline.answer("What is RPC?")
        assert llm.calls[0]["system_prompt"] == SYSTEM_PROMPT

    async def test_user_prompt_contains_context_and_question(self):
        chunks = [_chunk("c1", 0.9, filename="notes.pdf", content="RPC lets a client call a remote procedure.")]
        pipeline, _, llm = await self._pipeline(chunks)

        await pipeline.answer("What is RPC?")

        prompt = llm.calls[0]["user_prompt"]
        assert "notes.pdf" in prompt
        assert "RPC lets a client call a remote procedure." in prompt
        assert "Current Question:\nWhat is RPC?" in prompt

    async def test_history_is_included_when_present(self):
        from bson import ObjectId

        from app.models.message import Message, MessageRole

        history = [
            Message(
                conversation_id=ObjectId(),
                role=MessageRole.USER,
                content="What is distributed computing?",
            )
        ]
        pipeline, _, llm = await self._pipeline([_chunk("c1", 0.9)])

        await pipeline.answer("Follow-up question?", history=history)

        prompt = llm.calls[0]["user_prompt"]
        assert "Conversation History:" in prompt
        assert "What is distributed computing?" in prompt

    async def test_no_relevant_context_skips_the_llm_and_returns_fallback(self):
        chunks = [_chunk("c1", 0.2)]  # below default threshold
        pipeline, _, llm = await self._pipeline(chunks, min_relevance_score=0.5)

        result = await pipeline.answer("Unrelated question?")

        assert result.answer == NO_CONTEXT_ANSWER
        assert result.sources == []
        assert llm.calls == []  # LLM must not be called with no grounding

    async def test_debug_chunks_flag_which_sources_were_used(self):
        chunks = [_chunk("c1", 0.9), _chunk("c2", 0.2)]
        pipeline, _, _ = await self._pipeline(chunks, min_relevance_score=0.5)

        result = await pipeline.answer("question")

        used = {dc.chunk.chunk_id: dc.used for dc in result.debug_chunks}
        assert used["c1"] is True
        assert used["c2"] is False

    async def test_document_filter_is_forwarded_to_retrieval(self):
        pipeline, retrieval, _ = await self._pipeline([_chunk("c1", 0.9)])
        await pipeline.answer("question", document_ids=["doc-a", "doc-b"])
        assert retrieval.last_call["document_ids"] == ["doc-a", "doc-b"]

    async def test_answer_stream_starts_with_sources_then_streams_matching_text(self):
        chunks = [_chunk("c1", 0.9, page=42, filename="Distributed Systems.pdf")]
        pipeline, _, llm = await self._pipeline(chunks)

        events = [event async for event in pipeline.answer_stream("What is RPC?")]

        assert isinstance(events[0], StreamStart)
        assert len(events[0].sources) == 1
        assert events[0].sources[0].chunk_id == "c1"

        deltas = events[1:]
        assert deltas and all(isinstance(e, StreamDelta) for e in deltas)
        assert "".join(e.text for e in deltas) == llm.response

    async def test_answer_stream_no_relevant_context_skips_the_llm(self):
        chunks = [_chunk("c1", 0.2)]  # below default threshold
        pipeline, _, llm = await self._pipeline(chunks, min_relevance_score=0.5)

        events = [event async for event in pipeline.answer_stream("Unrelated question?")]

        assert isinstance(events[0], StreamStart)
        assert events[0].sources == []
        assert len(events) == 2
        assert events[1] == StreamDelta(text=NO_CONTEXT_ANSWER)
        assert llm.calls == []  # LLM must not be called with no grounding

    async def test_answer_stream_debug_chunks_flag_which_sources_were_used(self):
        chunks = [_chunk("c1", 0.9), _chunk("c2", 0.2)]
        pipeline, _, _ = await self._pipeline(chunks, min_relevance_score=0.5)

        events = [event async for event in pipeline.answer_stream("question")]

        used = {dc.chunk.chunk_id: dc.used for dc in events[0].debug_chunks}
        assert used["c1"] is True
        assert used["c2"] is False
