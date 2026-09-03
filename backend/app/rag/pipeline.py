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

from dataclasses import dataclass

from app.llm.base import LLMProvider
from app.logging_config import get_logger
from app.models.message import Message
from app.rag.context import ContextBuilder
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

    async def answer(
        self,
        question: str,
        *,
        document_ids: list[str] | None = None,
        history: list[Message] | None = None,
    ) -> RAGResult:
        history = history or []

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
            return RAGResult(answer=NO_CONTEXT_ANSWER, sources=[], debug_chunks=debug_chunks)

        context, source_refs = self._context_builder.build(relevant)
        used_chunk_ids = {ref.chunk.chunk_id for ref in source_refs}

        user_prompt = build_user_prompt(context=context, history=history, question=question)
        answer_text = await self._llm.generate(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)

        debug_chunks = [
            DebugChunk(chunk=c, used=c.chunk_id in used_chunk_ids) for c in retrieved
        ]
        return RAGResult(
            answer=answer_text,
            sources=[ref.chunk for ref in source_refs],
            debug_chunks=debug_chunks,
        )
