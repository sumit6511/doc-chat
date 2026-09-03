"""Orchestrates the full RAG flow: question -> retrieval -> context -> LLM -> answer.

    question
        v
    embed_query()
        v
    retrieve()               (RetrievalService -> Atlas $vectorSearch)
        v
    filter relevance
        v
    build_context()          (ContextBuilder)
        v
    build_prompt()           (rag/prompts.py)
        v
    generate()                (LLMProvider)
        v
    answer + sources

Deliberately kept free of API routing, MongoDB repository details, and the
concrete embedding/LLM implementations, so it can be unit tested with fakes.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from app.llm.base import LLMProvider
from app.logging_config import get_logger
from app.models.message import Message
from app.rag.context import ContextBuilder, SourceRef
from app.rag.prompts import NO_CONTEXT_ANSWER, SYSTEM_PROMPT, build_user_prompt
from app.rag.retrieval import RetrievalService, RetrievedChunk

logger = get_logger("docchat.rag")


@dataclass(frozen=True)
class DebugChunk:
    chunk: RetrievedChunk
    used: bool


@dataclass(frozen=True)
class RAGResult:
    answer: str
    sources: list[RetrievedChunk]
    debug_chunks: list[DebugChunk]


@dataclass(frozen=True)
class StreamStart:
    """First event of an answer_stream() call — carries the sources and debug
    info that's known up front, before any LLM tokens arrive."""

    sources: list[RetrievedChunk]
    debug_chunks: list[DebugChunk]


@dataclass(frozen=True)
class StreamDelta:
    """One incremental piece of the LLM's answer text."""

    text: str


class RAGPipeline:
    def __init__(
        self,
        retrieval_service: RetrievalService,
        context_builder: ContextBuilder,
        llm_provider: LLMProvider,
        *,
        top_k: int,
        num_candidates: int,
        min_relevance_score: float,
    ):
        self._retrieval = retrieval_service
        self._context_builder = context_builder
        self._llm = llm_provider
        self._top_k = top_k
        self._num_candidates = num_candidates
        self._min_relevance_score = min_relevance_score

    async def _retrieve_and_build_context(
        self, question: str, document_ids: list[str] | None
    ) -> tuple[str, list[SourceRef], list[DebugChunk], bool]:
        """Returns (context, source_refs, debug_chunks, no_context). When
        no_context is True, nothing was relevant enough to ground an answer
        and the caller must skip the LLM entirely."""
        retrieved = await self._retrieval.retrieve(
            question,
            top_k=self._top_k,
            num_candidates=self._num_candidates,
            document_ids=document_ids,
        )
        relevant = RetrievalService.filter_by_relevance(retrieved, self._min_relevance_score)

        if not relevant:
            logger.info("rag_no_relevant_context", retrieved=len(retrieved))
            debug_chunks = [DebugChunk(chunk=c, used=False) for c in retrieved]
            return "", [], debug_chunks, True

        context, source_refs = self._context_builder.build(relevant)
        used_chunk_ids = {ref.chunk.chunk_id for ref in source_refs}
        debug_chunks = [DebugChunk(chunk=c, used=c.chunk_id in used_chunk_ids) for c in retrieved]
        return context, source_refs, debug_chunks, False

    async def answer(
        self,
        question: str,
        *,
        document_ids: list[str] | None = None,
        history: list[Message] | None = None,
    ) -> RAGResult:
        history = history or []
        context, source_refs, debug_chunks, no_context = await self._retrieve_and_build_context(
            question, document_ids
        )
        if no_context:
            return RAGResult(answer=NO_CONTEXT_ANSWER, sources=[], debug_chunks=debug_chunks)

        user_prompt = build_user_prompt(context=context, history=history, question=question)
        answer_text = await self._llm.generate(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)

        return RAGResult(
            answer=answer_text,
            sources=[ref.chunk for ref in source_refs],
            debug_chunks=debug_chunks,
        )

    async def answer_stream(
        self,
        question: str,
        *,
        document_ids: list[str] | None = None,
        history: list[Message] | None = None,
    ) -> AsyncIterator[StreamStart | StreamDelta]:
        """Same retrieval/grounding behavior as answer(), but yields the LLM's
        response incrementally. Always yields exactly one StreamStart first,
        followed by zero or more StreamDelta events."""
        history = history or []
        context, source_refs, debug_chunks, no_context = await self._retrieve_and_build_context(
            question, document_ids
        )
        yield StreamStart(sources=[ref.chunk for ref in source_refs], debug_chunks=debug_chunks)

        if no_context:
            yield StreamDelta(text=NO_CONTEXT_ANSWER)
            return

        user_prompt = build_user_prompt(context=context, history=history, question=question)
        async for token in self._llm.generate_stream(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt):
            yield StreamDelta(text=token)
