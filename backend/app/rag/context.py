"""Formats retrieved chunks into the context block handed to the LLM.

ContextBuilder only formats — it never performs retrieval itself
(RetrievalService owns that) and never talks to the LLM (LLMProvider owns
that). Keeping it pure makes it trivial to unit test.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.rag.retrieval import RetrievedChunk

_SIMILARITY_DEDUPE_THRESHOLD = 0.97


@dataclass(frozen=True)
class SourceRef:
    """One entry in the numbered [Source N] list, paired 1:1 with a chunk."""

    index: int
    chunk: RetrievedChunk


class ContextBuilder:
    def __init__(self, max_context_chars: int = 6000):
        self._max_context_chars = max_context_chars

    def build(self, chunks: list[RetrievedChunk]) -> tuple[str, list[SourceRef]]:
        """Returns (formatted context block, ordered source references)."""
        deduped = self._deduplicate(chunks)

        sources: list[SourceRef] = []
        sections: list[str] = []
        total_chars = 0

        for i, chunk in enumerate(deduped, start=1):
            ref = SourceRef(index=i, chunk=chunk)
            section = (
                f"[Source {i}]\n"
                f"Document: {chunk.filename}\n"
                f"Page: {chunk.page_number}\n"
                f"Chunk ID: {chunk.chunk_id}\n\n"
                f"{chunk.content}"
            )
            if total_chars + len(section) > self._max_context_chars and sections:
                break
            sections.append(section)
            sources.append(ref)
            total_chars += len(section)

        return "\n\n".join(sections), sources

    @staticmethod
    def _deduplicate(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """Drops chunks whose content is (near-)identical to one already kept.

        Catches the common case of the same paragraph being chunked twice
        across overlapping page boundaries.
        """
        kept: list[RetrievedChunk] = []
        seen_normalized: list[str] = []
        for chunk in chunks:
            normalized = " ".join(chunk.content.split()).lower()
            if any(_similar_enough(normalized, other) for other in seen_normalized):
                continue
            kept.append(chunk)
            seen_normalized.append(normalized)
        return kept


def _similar_enough(a: str, b: str) -> bool:
    if a == b:
        return True
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if not shorter:
        return False
    # Cheap near-duplicate check: near-identical short chunks are usually a
    # prefix/suffix of one another after overlap-based chunking.
    return len(shorter) / len(longer) > _SIMILARITY_DEDUPE_THRESHOLD and shorter in longer
