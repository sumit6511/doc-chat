from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_chat_service
from app.config import Settings, get_settings
from app.errors import DocChatError, NotFoundError
from app.logging_config import get_logger
from app.models.conversation import Conversation
from app.models.message import Message
from app.rag.pipeline import DebugChunk
from app.schemas.chat import (
    DebugRetrievedChunk,
    MessageCreateRequest,
    MessageListResponse,
    MessageResponse,
    SourceSchema,
)
from app.schemas.conversation import (
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdateRequest,
)
from app.services.chat_service import ChatService, StreamDone

router = APIRouter(prefix="/conversations", tags=["conversations"])
logger = get_logger("docchat.api.conversations")


def _parse_object_id(raw_id: str, *, not_found_message: str = "Conversation not found.") -> ObjectId:
    try:
        return ObjectId(raw_id)
    except (InvalidId, TypeError) as exc:
        raise NotFoundError(not_found_message) from exc


async def _to_conversation_response(
    conversation: Conversation, service: ChatService
) -> ConversationResponse:
    message_count = await service.count_messages(conversation.id)
    return ConversationResponse(
        id=str(conversation.id),
        title=conversation.title,
        document_ids=[str(doc_id) for doc_id in conversation.document_ids],
        message_count=message_count,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def _to_message_response(
    message: Message, debug_chunks: list[DebugChunk] | None = None
) -> MessageResponse:
    debug_payload = None
    if debug_chunks is not None:
        debug_payload = [
            DebugRetrievedChunk(
                filename=dc.chunk.filename,
                page_number=dc.chunk.page_number,
                score=dc.chunk.similarity_score,
                used=dc.used,
            )
            for dc in debug_chunks
        ]

    return MessageResponse(
        id=str(message.id),
        conversation_id=str(message.conversation_id),
        role=message.role,
        content=message.content,
        sources=[
            SourceSchema(
                chunk_id=str(s.chunk_id),
                document_id=str(s.document_id),
                filename=s.filename,
                page_number=s.page_number,
                similarity_score=s.similarity_score,
            )
            for s in message.sources
        ],
        debug_retrieved_chunks=debug_payload,
        created_at=message.created_at,
    )


@router.get("", response_model=ConversationListResponse, summary="List conversations")
async def list_conversations(
    service: ChatService = Depends(get_chat_service),
) -> ConversationListResponse:
    conversations = await service.list_conversations()
    responses = await asyncio.gather(
        *(_to_conversation_response(c, service) for c in conversations)
    )
    return ConversationListResponse(conversations=list(responses), total=len(responses))


@router.post("", response_model=ConversationResponse, status_code=201, summary="Start a new conversation")
async def create_conversation(
    payload: ConversationCreateRequest, service: ChatService = Depends(get_chat_service)
) -> ConversationResponse:
    conversation = await service.create_conversation(payload.document_ids, payload.title)
    return await _to_conversation_response(conversation, service)


@router.get("/{conversation_id}", response_model=ConversationResponse, summary="Get a conversation")
async def get_conversation(
    conversation_id: str, service: ChatService = Depends(get_chat_service)
) -> ConversationResponse:
    conversation = await service.get_conversation(_parse_object_id(conversation_id))
    return await _to_conversation_response(conversation, service)


@router.patch(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Rename a conversation or change its document scope",
)
async def update_conversation(
    conversation_id: str,
    payload: ConversationUpdateRequest,
    service: ChatService = Depends(get_chat_service),
) -> ConversationResponse:
    conversation = await service.update_conversation(
        _parse_object_id(conversation_id),
        title=payload.title,
        document_ids=payload.document_ids,
    )
    return await _to_conversation_response(conversation, service)


@router.delete(
    "/{conversation_id}",
    status_code=204,
    response_model=None,
    summary="Delete a conversation and its messages",
)
async def delete_conversation(
    conversation_id: str, service: ChatService = Depends(get_chat_service)
) -> None:
    await service.delete_conversation(_parse_object_id(conversation_id))


@router.get(
    "/{conversation_id}/messages", response_model=MessageListResponse, summary="List messages"
)
async def list_messages(
    conversation_id: str, service: ChatService = Depends(get_chat_service)
) -> MessageListResponse:
    messages = await service.list_messages(_parse_object_id(conversation_id))
    return MessageListResponse(messages=[_to_message_response(m) for m in messages])


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=201,
    summary="Ask a question and get a grounded, cited answer",
    description=(
        "Runs the full RAG pipeline: embeds the question, retrieves relevant "
        "chunks via MongoDB Atlas Vector Search (scoped to the conversation's "
        "documents when set), builds context, and generates an answer. The "
        "response always carries the source chunks actually used."
    ),
)
async def post_message(
    conversation_id: str,
    payload: MessageCreateRequest,
    settings: Settings = Depends(get_settings),
    service: ChatService = Depends(get_chat_service),
) -> MessageResponse:
    assistant_message, debug_chunks = await service.post_message(
        _parse_object_id(conversation_id), payload.content
    )
    return _to_message_response(assistant_message, debug_chunks if settings.debug_rag else None)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.post(
    "/{conversation_id}/messages/stream",
    summary="Ask a question and stream a grounded, cited answer via Server-Sent Events",
    description=(
        "Same as POST /messages, but streams the answer as it's generated "
        "instead of waiting for the full response. Emits a text/event-stream "
        "body of JSON-payload SSE events: {type: 'delta', text} for each "
        "incremental piece of the answer, then one {type: 'done', message} "
        "carrying the full persisted message (with sources), or "
        "{type: 'error', message, code} if generation fails partway through."
    ),
)
async def post_message_stream(
    conversation_id: str,
    payload: MessageCreateRequest,
    settings: Settings = Depends(get_settings),
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    conv_id = _parse_object_id(conversation_id)

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for event in service.post_message_stream(conv_id, payload.content):
                if isinstance(event, StreamDone):
                    message_response = _to_message_response(
                        event.message, event.debug_chunks if settings.debug_rag else None
                    )
                    yield _sse({"type": "done", "message": json.loads(message_response.model_dump_json())})
                else:
                    yield _sse({"type": "delta", "text": event.text})
        except DocChatError as exc:
            yield _sse({"type": "error", "message": exc.message, "code": exc.code})
        except Exception:
            logger.exception("stream_message_failed", conversation_id=conv_id)
            yield _sse(
                {
                    "type": "error",
                    "message": "Something went wrong generating a response.",
                    "code": "INTERNAL_ERROR",
                }
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
