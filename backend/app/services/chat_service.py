"""Conversation/message lifecycle and orchestration of the RAG pipeline per turn."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from bson import ObjectId
from bson.errors import InvalidId

from app.db.repositories.conversations import ConversationRepository
from app.db.repositories.documents import DocumentRepository
from app.db.repositories.messages import MessageRepository
from app.errors import NotFoundError, ValidationFailedError
from app.logging_config import get_logger
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole, MessageSource
from app.rag.pipeline import DebugChunk, RAGPipeline, StreamDelta, StreamStart

logger = get_logger("docchat.chat")

_DEFAULT_TITLE = "New Conversation"
_TITLE_MAX_CHARS = 60


@dataclass(frozen=True)
class StreamDone:
    """Final event of post_message_stream() — the persisted assistant message."""

    message: Message
    debug_chunks: list[DebugChunk]


def _to_object_ids(document_ids: list[str]) -> list[ObjectId]:
    """Converts request-supplied id strings, raising a clean 404 (rather than
    letting bson.errors.InvalidId bubble up as a raw 500) if any are malformed
    — an invalid id can never resolve to a real document either way."""
    try:
        return [ObjectId(doc_id) for doc_id in document_ids]
    except InvalidId as exc:
        raise NotFoundError("One or more selected documents were not found.") from exc


def generate_title_from_text(text: str) -> str:
    """Heuristic (non-LLM) conversation title from the first user question."""
    collapsed = " ".join(text.split())
    if len(collapsed) <= _TITLE_MAX_CHARS:
        return collapsed or _DEFAULT_TITLE
    return collapsed[:_TITLE_MAX_CHARS].rsplit(" ", 1)[0] + "…"


class ChatService:
    def __init__(
        self,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
        document_repository: DocumentRepository,
        rag_pipeline: RAGPipeline,
        *,
        max_history_messages: int,
    ):
        self._conversations = conversation_repository
        self._messages = message_repository
        self._documents = document_repository
        self._rag = rag_pipeline
        self._max_history_messages = max_history_messages

    async def create_conversation(
        self, document_ids: list[str], title: str | None = None
    ) -> Conversation:
        object_ids = _to_object_ids(document_ids)
        if object_ids and not await self._documents.exist(object_ids):
            raise NotFoundError("One or more selected documents were not found.")

        conversation = Conversation(title=title or _DEFAULT_TITLE, document_ids=object_ids)
        return await self._conversations.create(conversation)

    async def list_conversations(self) -> list[Conversation]:
        return await self._conversations.list_all()

    async def get_conversation(self, conversation_id: ObjectId) -> Conversation:
        conversation = await self._conversations.get_by_id(conversation_id)
        if conversation is None:
            raise NotFoundError("Conversation not found.")
        return conversation

    async def update_conversation(
        self,
        conversation_id: ObjectId,
        *,
        title: str | None = None,
        document_ids: list[str] | None = None,
    ) -> Conversation:
        await self.get_conversation(conversation_id)
        updates: dict = {}
        if title is not None:
            updates["title"] = title
        if document_ids is not None:
            object_ids = _to_object_ids(document_ids)
            if object_ids and not await self._documents.exist(object_ids):
                raise NotFoundError("One or more selected documents were not found.")
            updates["document_ids"] = object_ids
        if updates:
            await self._conversations.update(conversation_id, updates)
        return await self.get_conversation(conversation_id)

    async def delete_conversation(self, conversation_id: ObjectId) -> None:
        await self.get_conversation(conversation_id)
        await self._messages.delete_by_conversation(conversation_id)
        await self._conversations.delete(conversation_id)
        logger.info("conversation_deleted", conversation_id=conversation_id)

    async def list_messages(self, conversation_id: ObjectId) -> list[Message]:
        await self.get_conversation(conversation_id)
        return await self._messages.list_by_conversation(conversation_id)

    async def count_messages(self, conversation_id: ObjectId) -> int:
        return await self._messages.count_by_conversation(conversation_id)

    async def post_message(
        self, conversation_id: ObjectId, content: str
    ) -> tuple[Message, list[DebugChunk]]:
        content = content.strip()
        if not content:
            raise ValidationFailedError("Message content cannot be empty.")

        conversation = await self.get_conversation(conversation_id)

        history = await self._messages.list_recent(conversation_id, self._max_history_messages)
        is_first_message = len(history) == 0

        await self._messages.create(
            Message(conversation_id=conversation_id, role=MessageRole.USER, content=content)
        )

        document_ids = [str(doc_id) for doc_id in conversation.document_ids] or None
        result = await self._rag.answer(content, document_ids=document_ids, history=history)

        sources = [
            MessageSource(
                chunk_id=ObjectId(chunk.chunk_id),
                document_id=ObjectId(chunk.document_id),
                filename=chunk.filename,
                page_number=chunk.page_number,
                similarity_score=chunk.similarity_score,
            )
            for chunk in result.sources
        ]
        assistant_message = await self._messages.create(
            Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=result.answer,
                sources=sources,
            )
        )

        conversation_updates: dict = {}
        if is_first_message and conversation.title == _DEFAULT_TITLE:
            conversation_updates["title"] = generate_title_from_text(content)
        if conversation_updates:
            await self._conversations.update(conversation_id, conversation_updates)
        else:
            await self._conversations.touch(conversation_id)

        logger.info(
            "chat_turn_completed",
            conversation_id=conversation_id,
            retrieved=len(result.debug_chunks),
            used_sources=len(sources),
        )

        return assistant_message, result.debug_chunks

    async def post_message_stream(
        self, conversation_id: ObjectId, content: str
    ) -> AsyncIterator[StreamDelta | StreamDone]:
        """Same behavior as post_message(), but yields the assistant's answer
        incrementally as StreamDelta events, followed by one final StreamDone
        once the full message has been generated and persisted."""
        content = content.strip()
        if not content:
            raise ValidationFailedError("Message content cannot be empty.")

        conversation = await self.get_conversation(conversation_id)

        history = await self._messages.list_recent(conversation_id, self._max_history_messages)
        is_first_message = len(history) == 0

        await self._messages.create(
            Message(conversation_id=conversation_id, role=MessageRole.USER, content=content)
        )

        document_ids = [str(doc_id) for doc_id in conversation.document_ids] or None

        answer_parts: list[str] = []
        sources: list[MessageSource] = []
        debug_chunks: list[DebugChunk] = []

        async for event in self._rag.answer_stream(content, document_ids=document_ids, history=history):
            if isinstance(event, StreamStart):
                debug_chunks = event.debug_chunks
                sources = [
                    MessageSource(
                        chunk_id=ObjectId(chunk.chunk_id),
                        document_id=ObjectId(chunk.document_id),
                        filename=chunk.filename,
                        page_number=chunk.page_number,
                        similarity_score=chunk.similarity_score,
                    )
                    for chunk in event.sources
                ]
            else:
                answer_parts.append(event.text)
                yield event

        assistant_message = await self._messages.create(
            Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content="".join(answer_parts),
                sources=sources,
            )
        )

        conversation_updates: dict = {}
        if is_first_message and conversation.title == _DEFAULT_TITLE:
            conversation_updates["title"] = generate_title_from_text(content)
        if conversation_updates:
            await self._conversations.update(conversation_id, conversation_updates)
        else:
            await self._conversations.touch(conversation_id)

        logger.info(
            "chat_turn_completed",
            conversation_id=conversation_id,
            retrieved=len(debug_chunks),
            used_sources=len(sources),
        )

        yield StreamDone(message=assistant_message, debug_chunks=debug_chunks)
