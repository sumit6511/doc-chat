"""Prompt construction for the RAG pipeline."""

from __future__ import annotations

from app.models.message import Message, MessageRole

SYSTEM_PROMPT = """You are DocChat, an AI assistant that answers questions using uploaded document context.

Rules:

1. Use only the supplied document context.
2. Do not fabricate information.
3. If the answer is not supported by the context, explicitly say that the documents do not contain enough information.
4. Answer clearly and directly, in plain prose.
5. Use conversation history only to understand the current question.
6. Do not treat previous assistant answers as authoritative evidence.
7. The context below is labeled "[Source 1]", "[Source 2]", etc. with a Document/Page/Chunk ID for each passage — that labeling is for your reference only. Do not repeat those labels, document names, page numbers, or chunk IDs in your answer; the application displays the source documents separately. Just answer the question in normal prose, as if you already knew the material."""

NO_CONTEXT_ANSWER = "I couldn't find enough information in your documents to answer that question."


def build_history_block(history: list[Message]) -> str:
    if not history:
        return ""
    lines = []
    for message in history:
        speaker = "User" if message.role == MessageRole.USER else "Assistant"
        lines.append(f"{speaker}: {message.content}")
    return "\n".join(lines)


def build_user_prompt(*, context: str, history: list[Message], question: str) -> str:
    history_block = build_history_block(history)

    parts = [f"Context:\n{context}" if context else "Context:\n(no relevant context retrieved)"]

    if history_block:
        parts.append(f"Conversation History:\n{history_block}")

    parts.append(f"Current Question:\n{question}")

    return "\n\n".join(parts)
