"""Paragraph/sentence-aware text chunking.

Chunk size and overlap are expressed in words, used as an approximate proxy
for tokens (see CHUNK_SIZE / CHUNK_OVERLAP in .env.example) — this keeps the
service dependency-free while staying close enough to real token counts for
a MiniLM-class embedding model. The chunker is deterministic: the same input
and settings always produce the same chunks.

Chunking runs per PDF page (see IngestionService), so a chunk's `page_number`
is always exact and citations never need to guess which page a chunk came
from.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n+")
_WHITESPACE_RE = re.compile(r"[ \t\f\v]+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


@dataclass(frozen=True)
class TextChunk:
    content: str
    chunk_index: int
    word_count: int


def normalize_whitespace(text: str) -> str:
    """Collapses runs of spaces/tabs and trims lines, while keeping paragraph breaks."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [_WHITESPACE_RE.sub(" ", line).strip() for line in text.split("\n")]
    normalized = "\n".join(lines)
    # Collapse 3+ consecutive newlines down to a single paragraph break.
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def split_into_paragraphs(text: str) -> list[str]:
    if not text:
        return []
    paragraphs = _PARAGRAPH_SPLIT_RE.split(text)
    return [p.strip() for p in paragraphs if p.strip()]


def split_into_sentences(paragraph: str) -> list[str]:
    if not paragraph:
        return []
    sentences = _SENTENCE_SPLIT_RE.split(paragraph.replace("\n", " ").strip())
    return [s.strip() for s in sentences if s.strip()]


def _split_long_sentence(sentence: str, max_words: int) -> list[str]:
    """Fallback for a single sentence longer than the whole chunk budget."""
    words = sentence.split()
    return [" ".join(words[i : i + max_words]) for i in range(0, len(words), max_words)] or []


def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> list[TextChunk]:
    """Splits `text` into overlapping chunks of ~`chunk_size` words.

    Prefers paragraph boundaries, then sentence boundaries, so sentences are
    only ever split when a single sentence alone exceeds `chunk_size`.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and < chunk_size")

    normalized = normalize_whitespace(text)
    if not normalized:
        return []

    sentences: list[str] = []
    for paragraph in split_into_paragraphs(normalized):
        para_sentences = split_into_sentences(paragraph)
        for sentence in para_sentences:
            word_count = len(sentence.split())
            if word_count > chunk_size:
                sentences.extend(_split_long_sentence(sentence, chunk_size))
            else:
                sentences.append(sentence)

    if not sentences:
        return []

    chunks: list[TextChunk] = []
    current_words: list[str] = []

    def flush() -> list[str]:
        """Finalizes the current chunk and returns the overlap words to seed the next one."""
        if not current_words:
            return []
        content = " ".join(current_words)
        chunks.append(TextChunk(content=content, chunk_index=len(chunks), word_count=len(current_words)))
        if chunk_overlap == 0:
            return []
        return current_words[-chunk_overlap:]

    for sentence in sentences:
        sentence_words = sentence.split()
        projected_len = len(current_words) + len(sentence_words)
        if current_words and projected_len > chunk_size:
            overlap_words = flush()
            current_words = list(overlap_words)
        current_words.extend(sentence_words)

    if current_words:
        flush()

    return chunks
