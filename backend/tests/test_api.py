import json

import pytest
from bson import ObjectId

from app.config import Settings, get_settings
from app.main import app as fastapi_app
from tests.conftest import make_minimal_pdf_bytes


async def _collect_sse_events(response) -> list[dict]:
    events = []
    async for line in response.aiter_lines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: ") :]))
    return events


@pytest.mark.asyncio
class TestHealthEndpoint:
    async def test_health_returns_200_with_expected_shape(self, api_client):
        response = await api_client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) == {"status", "database", "vector_search", "llm"}
        assert body["database"] == "ok"
        assert body["llm"] == "ok"

    async def test_health_reports_unavailable_instead_of_crashing_when_db_is_down(
        self, api_client
    ):
        """Regression test: a database that was never connected (e.g. Atlas
        unreachable at startup) must make /api/health report "unavailable",
        not raise — this endpoint is the one place that must stay up and
        informative even when every dependency is down."""
        from app.db.client import get_database_or_none

        fastapi_app.dependency_overrides[get_database_or_none] = lambda: None

        response = await api_client.get("/api/health")

        assert response.status_code == 200
        body = response.json()
        assert body["database"] == "unavailable"
        assert body["vector_search"] == "unknown"
        assert body["status"] == "degraded"


@pytest.mark.asyncio
class TestDocumentUpload:
    async def test_rejects_non_pdf_extension(self, api_client):
        files = {"file": ("notes.txt", b"just some text", "text/plain")}
        response = await api_client.post("/api/documents", files=files)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"

    async def test_rejects_empty_file(self, api_client):
        files = {"file": ("notes.pdf", b"", "application/pdf")}
        response = await api_client.post("/api/documents", files=files)
        assert response.status_code == 400

    async def test_rejects_corrupted_pdf(self, api_client):
        files = {"file": ("notes.pdf", b"%PDF-1.4 not really a pdf", "application/pdf")}
        response = await api_client.post("/api/documents", files=files)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "CORRUPTED_FILE"

    async def test_rejects_oversized_file(self, api_client):
        tiny_limit_settings = Settings(max_file_size_mb=0)
        fastapi_app.dependency_overrides[get_settings] = lambda: tiny_limit_settings
        try:
            files = {"file": ("notes.pdf", make_minimal_pdf_bytes(), "application/pdf")}
            response = await api_client.post("/api/documents", files=files)
            assert response.status_code == 413
            assert response.json()["error"]["code"] == "FILE_TOO_LARGE"
        finally:
            del fastapi_app.dependency_overrides[get_settings]

    async def test_accepts_valid_pdf_and_returns_processing_status(self, api_client):
        files = {
            "file": ("Distributed Systems.pdf", make_minimal_pdf_bytes(pages=3), "application/pdf")
        }
        response = await api_client.post("/api/documents", files=files)
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "PROCESSING"
        assert body["original_filename"] == "Distributed Systems.pdf"
        assert body["page_count"] == 3


@pytest.mark.asyncio
class TestDocumentListing:
    async def test_list_documents_returns_uploaded_documents(self, api_client):
        files = {"file": ("a.pdf", make_minimal_pdf_bytes(), "application/pdf")}
        await api_client.post("/api/documents", files=files)

        response = await api_client.get("/api/documents")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["documents"][0]["original_filename"] == "a.pdf"

    async def test_listed_document_id_is_usable_for_a_follow_up_get(self, api_client):
        """Regression test: a document's `id` as returned by GET /documents
        (a fresh read from Mongo) must be a real, usable id — not the id
        captured only at creation time. This is the exact bug class where
        MongoBaseModel.id lacked alias="_id": every record read back via
        list_all()/get_by_id() silently got id=None (serialized as the
        string "None"), which then 404'd on any follow-up request."""
        files = {"file": ("a.pdf", make_minimal_pdf_bytes(), "application/pdf")}
        await api_client.post("/api/documents", files=files)

        list_response = await api_client.get("/api/documents")
        listed_id = list_response.json()["documents"][0]["id"]

        assert ObjectId.is_valid(listed_id), f"expected a real ObjectId, got {listed_id!r}"

        get_response = await api_client.get(f"/api/documents/{listed_id}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == listed_id

    async def test_get_missing_document_returns_404(self, api_client):
        response = await api_client.get(f"/api/documents/{ObjectId()}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"

    async def test_get_document_with_malformed_id_returns_404(self, api_client):
        response = await api_client.get("/api/documents/not-a-valid-id")
        assert response.status_code == 404

    async def test_delete_document(self, api_client):
        files = {"file": ("a.pdf", make_minimal_pdf_bytes(), "application/pdf")}
        upload = await api_client.post("/api/documents", files=files)
        document_id = upload.json()["id"]

        delete_response = await api_client.delete(f"/api/documents/{document_id}")
        assert delete_response.status_code == 204

        get_response = await api_client.get(f"/api/documents/{document_id}")
        assert get_response.status_code == 404


@pytest.mark.asyncio
class TestConversations:
    async def test_create_conversation(self, api_client):
        response = await api_client.post("/api/conversations", json={"document_ids": []})
        assert response.status_code == 201
        body = response.json()
        assert body["title"] == "New Conversation"
        assert body["document_ids"] == []

    async def test_create_conversation_with_unknown_document_returns_404(self, api_client):
        response = await api_client.post(
            "/api/conversations", json={"document_ids": [str(ObjectId())]}
        )
        assert response.status_code == 404

    async def test_list_conversations(self, api_client):
        await api_client.post("/api/conversations", json={"document_ids": []})
        response = await api_client.get("/api/conversations")
        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_listed_conversation_id_is_usable_to_revisit_it(self, api_client):
        """Regression test, mirroring the document one above: a conversation
        id as returned by GET /conversations (a fresh Mongo read) must work
        for revisiting that conversation and its messages — this is exactly
        the "conversation not found" symptom the id=None bug produced on any
        second visit (list -> open), as opposed to the first visit right
        after creation (which used the creation response's id directly)."""
        create = await api_client.post("/api/conversations", json={"document_ids": []})
        await api_client.post(
            f"/api/conversations/{create.json()['id']}/messages", json={"content": "Hello?"}
        )

        list_response = await api_client.get("/api/conversations")
        listed_id = list_response.json()["conversations"][0]["id"]
        assert ObjectId.is_valid(listed_id), f"expected a real ObjectId, got {listed_id!r}"

        get_response = await api_client.get(f"/api/conversations/{listed_id}")
        assert get_response.status_code == 200

        messages_response = await api_client.get(f"/api/conversations/{listed_id}/messages")
        assert messages_response.status_code == 200
        assert len(messages_response.json()["messages"]) == 2

    async def test_rename_conversation(self, api_client):
        create = await api_client.post("/api/conversations", json={"document_ids": []})
        conversation_id = create.json()["id"]

        response = await api_client.patch(
            f"/api/conversations/{conversation_id}",
            json={"title": "Distributed Systems Concepts"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Distributed Systems Concepts"

    async def test_delete_conversation(self, api_client):
        create = await api_client.post("/api/conversations", json={"document_ids": []})
        conversation_id = create.json()["id"]

        response = await api_client.delete(f"/api/conversations/{conversation_id}")
        assert response.status_code == 204

        get_response = await api_client.get(f"/api/conversations/{conversation_id}")
        assert get_response.status_code == 404


@pytest.mark.asyncio
class TestMessages:
    async def test_post_message_returns_grounded_answer_with_sources(
        self, api_client, fake_rag_pipeline
    ):
        create = await api_client.post("/api/conversations", json={"document_ids": []})
        conversation_id = create.json()["id"]

        response = await api_client.post(
            f"/api/conversations/{conversation_id}/messages", json={"content": "What is RPC?"}
        )
        assert response.status_code == 201
        body = response.json()
        assert body["role"] == "assistant"
        assert body["content"] == fake_rag_pipeline.result.answer
        assert len(body["sources"]) == 1
        assert body["sources"][0]["filename"] == "sample.pdf"

    async def test_first_message_sets_conversation_title(self, api_client):
        create = await api_client.post("/api/conversations", json={"document_ids": []})
        conversation_id = create.json()["id"]

        await api_client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "What are the main characteristics of distributed systems?"},
        )

        get_response = await api_client.get(f"/api/conversations/{conversation_id}")
        assert get_response.json()["title"].startswith("What are the main characteristics")

    async def test_empty_message_is_rejected(self, api_client):
        create = await api_client.post("/api/conversations", json={"document_ids": []})
        conversation_id = create.json()["id"]

        response = await api_client.post(
            f"/api/conversations/{conversation_id}/messages", json={"content": "   "}
        )
        assert response.status_code == 422

    async def test_message_for_missing_conversation_returns_404(self, api_client):
        response = await api_client.post(
            f"/api/conversations/{ObjectId()}/messages", json={"content": "Hello?"}
        )
        assert response.status_code == 404

    async def test_messages_are_listed_in_order(self, api_client):
        create = await api_client.post("/api/conversations", json={"document_ids": []})
        conversation_id = create.json()["id"]

        await api_client.post(
            f"/api/conversations/{conversation_id}/messages", json={"content": "First question?"}
        )
        response = await api_client.get(f"/api/conversations/{conversation_id}/messages")
        assert response.status_code == 200
        roles = [m["role"] for m in response.json()["messages"]]
        assert roles == ["user", "assistant"]


@pytest.mark.asyncio
class TestMessagesStream:
    async def test_stream_emits_deltas_then_a_done_event_with_the_full_message(
        self, api_client, fake_rag_pipeline
    ):
        create = await api_client.post("/api/conversations", json={"document_ids": []})
        conversation_id = create.json()["id"]

        async with api_client.stream(
            "POST",
            f"/api/conversations/{conversation_id}/messages/stream",
            json={"content": "What is RPC?"},
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            events = await _collect_sse_events(response)

        assert events, "expected at least one SSE event"
        assert all(e["type"] in {"delta", "done"} for e in events)

        deltas = [e for e in events if e["type"] == "delta"]
        assert deltas, "expected at least one delta event"
        streamed_text = "".join(e["text"] for e in deltas)
        assert streamed_text == fake_rag_pipeline.result.answer

        done_events = [e for e in events if e["type"] == "done"]
        assert len(done_events) == 1
        message = done_events[0]["message"]
        assert message["role"] == "assistant"
        assert message["content"] == fake_rag_pipeline.result.answer
        assert len(message["sources"]) == 1
        assert message["sources"][0]["filename"] == "sample.pdf"

    async def test_stream_persists_the_assistant_message(self, api_client):
        create = await api_client.post("/api/conversations", json={"document_ids": []})
        conversation_id = create.json()["id"]

        async with api_client.stream(
            "POST",
            f"/api/conversations/{conversation_id}/messages/stream",
            json={"content": "What is RPC?"},
        ) as response:
            await _collect_sse_events(response)

        messages_response = await api_client.get(f"/api/conversations/{conversation_id}/messages")
        roles = [m["role"] for m in messages_response.json()["messages"]]
        assert roles == ["user", "assistant"]

    async def test_stream_for_missing_conversation_emits_an_error_event(self, api_client):
        async with api_client.stream(
            "POST",
            f"/api/conversations/{ObjectId()}/messages/stream",
            json={"content": "Hello?"},
        ) as response:
            # Headers are already committed to 200 by the time the handler
            # discovers the conversation doesn't exist — the error surfaces
            # as an SSE event instead of an HTTP status code.
            assert response.status_code == 200
            events = await _collect_sse_events(response)

        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert events[0]["code"] == "NOT_FOUND"

    async def test_stream_empty_message_emits_an_error_event(self, api_client):
        create = await api_client.post("/api/conversations", json={"document_ids": []})
        conversation_id = create.json()["id"]

        async with api_client.stream(
            "POST",
            f"/api/conversations/{conversation_id}/messages/stream",
            json={"content": "   "},
        ) as response:
            assert response.status_code == 200
            events = await _collect_sse_events(response)

        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert events[0]["code"] == "VALIDATION_FAILED"
