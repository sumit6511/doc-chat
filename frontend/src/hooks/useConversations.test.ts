import { act, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { conversationsApi } from "@/api/conversations";
import {
  conversationKey,
  conversationsKey,
  messagesKey,
  useConversationQuery,
  useConversationsQuery,
  useCreateConversationMutation,
  useDeleteConversationMutation,
  useMessagesQuery,
  useRenameConversationMutation,
  useSendMessageStream,
  useUpdateConversationDocumentsMutation,
} from "@/hooks/useConversations";
import { createTestQueryClient, renderHookWithClient } from "@/test/queryTestUtils";
import type { Conversation, Message } from "@/types";

vi.mock("@/api/conversations", () => ({
  conversationsApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    rename: vi.fn(),
    updateDocuments: vi.fn(),
    remove: vi.fn(),
    listMessages: vi.fn(),
    streamMessage: vi.fn(),
  },
}));

const mockedConversationsApi = vi.mocked(conversationsApi);

function makeConversation(overrides: Partial<Conversation> = {}): Conversation {
  return {
    id: "conv-1",
    title: "New Conversation",
    document_ids: [],
    message_count: 0,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

function makeMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: "msg-1",
    conversation_id: "conv-1",
    role: "assistant",
    content: "Hello",
    sources: [],
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useConversationsQuery", () => {
  it("returns the conversation list from the API", async () => {
    const response = { conversations: [makeConversation()], total: 1 };
    mockedConversationsApi.list.mockResolvedValue(response);

    const { result } = renderHookWithClient(() => useConversationsQuery());

    await waitFor(() => expect(result.current.data).toEqual(response));
  });
});

describe("useConversationQuery", () => {
  it("fetches the conversation when an id is provided", async () => {
    const conversation = makeConversation({ id: "conv-42" });
    mockedConversationsApi.get.mockResolvedValue(conversation);

    const { result } = renderHookWithClient(() => useConversationQuery("conv-42"));

    await waitFor(() => expect(result.current.data).toEqual(conversation));
    expect(mockedConversationsApi.get).toHaveBeenCalledWith("conv-42");
  });

  it("does not fetch when no id is provided", () => {
    const { result } = renderHookWithClient(() => useConversationQuery(undefined));

    expect(result.current.fetchStatus).toBe("idle");
    expect(mockedConversationsApi.get).not.toHaveBeenCalled();
  });
});

describe("useCreateConversationMutation", () => {
  it("calls conversationsApi.create and invalidates the conversation list", async () => {
    const created = makeConversation();
    mockedConversationsApi.create.mockResolvedValue(created);
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHookWithClient(() => useCreateConversationMutation(), { queryClient });

    result.current.mutate({ documentIds: ["doc-1"], title: "Test" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedConversationsApi.create).toHaveBeenCalledWith(["doc-1"], "Test");
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: conversationsKey });
  });
});

describe("useRenameConversationMutation", () => {
  it("renames and invalidates both the list and the specific conversation", async () => {
    mockedConversationsApi.rename.mockResolvedValue(makeConversation({ title: "Renamed" }));
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHookWithClient(() => useRenameConversationMutation(), { queryClient });

    result.current.mutate({ id: "conv-1", title: "Renamed" });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedConversationsApi.rename).toHaveBeenCalledWith("conv-1", "Renamed");
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: conversationsKey });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: conversationKey("conv-1") });
  });
});

describe("useUpdateConversationDocumentsMutation", () => {
  it("updates document scope and invalidates the list and the specific conversation", async () => {
    mockedConversationsApi.updateDocuments.mockResolvedValue(
      makeConversation({ document_ids: ["doc-9"] })
    );
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHookWithClient(() => useUpdateConversationDocumentsMutation(), {
      queryClient,
    });

    result.current.mutate({ id: "conv-1", documentIds: ["doc-9"] });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedConversationsApi.updateDocuments).toHaveBeenCalledWith("conv-1", ["doc-9"]);
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: conversationsKey });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: conversationKey("conv-1") });
  });
});

describe("useDeleteConversationMutation", () => {
  it("calls conversationsApi.remove and invalidates the conversation list", async () => {
    mockedConversationsApi.remove.mockResolvedValue(undefined);
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHookWithClient(() => useDeleteConversationMutation(), { queryClient });

    result.current.mutate("conv-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedConversationsApi.remove).toHaveBeenCalledWith("conv-1");
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: conversationsKey });
  });
});

describe("useMessagesQuery", () => {
  it("fetches messages for the given conversation", async () => {
    const response = { messages: [makeMessage()] };
    mockedConversationsApi.listMessages.mockResolvedValue(response);

    const { result } = renderHookWithClient(() => useMessagesQuery("conv-1"));

    await waitFor(() => expect(result.current.data).toEqual(response));
    expect(mockedConversationsApi.listMessages).toHaveBeenCalledWith("conv-1");
  });

  it("does not fetch when no conversation id is provided", () => {
    const { result } = renderHookWithClient(() => useMessagesQuery(undefined));

    expect(result.current.fetchStatus).toBe("idle");
    expect(mockedConversationsApi.listMessages).not.toHaveBeenCalled();
  });
});

describe("useSendMessageStream", () => {
  it("streams delta text into assistantText, then invalidates queries once done", async () => {
    mockedConversationsApi.streamMessage.mockImplementation(async function* () {
      yield { type: "delta", text: "RPC " };
      yield { type: "delta", text: "allows a client." };
      yield { type: "done", message: makeMessage({ content: "RPC allows a client." }) };
    });
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHookWithClient(() => useSendMessageStream("conv-1"), { queryClient });

    act(() => {
      result.current.send("What is RPC?");
    });

    await waitFor(() => expect(result.current.status).toBe("idle"));
    expect(mockedConversationsApi.streamMessage).toHaveBeenCalledWith("conv-1", "What is RPC?");
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: messagesKey("conv-1") });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: conversationsKey });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: conversationKey("conv-1") });
  });

  it("accumulates delta text while streaming, before the stream completes", async () => {
    let releaseSecondDelta = () => {};
    const secondDeltaGate = new Promise<void>((resolve) => {
      releaseSecondDelta = resolve;
    });
    mockedConversationsApi.streamMessage.mockImplementation(async function* () {
      yield { type: "delta", text: "RPC " };
      await secondDeltaGate;
      yield { type: "delta", text: "allows a client." };
      yield { type: "done", message: makeMessage() };
    });

    const { result } = renderHookWithClient(() => useSendMessageStream("conv-1"));

    act(() => {
      result.current.send("What is RPC?");
    });

    await waitFor(() => expect(result.current.assistantText).toBe("RPC "));
    expect(result.current.status).toBe("streaming");

    releaseSecondDelta();
    await waitFor(() => expect(result.current.status).toBe("idle"));
  });

  it("sets an error status and message when the stream emits an error event", async () => {
    mockedConversationsApi.streamMessage.mockImplementation(async function* () {
      yield { type: "error", message: "The AI service is unavailable.", code: "LLM_UNAVAILABLE" };
    });
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHookWithClient(() => useSendMessageStream("conv-1"), { queryClient });

    act(() => {
      result.current.send("What is RPC?");
    });

    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.errorMessage).toBe("The AI service is unavailable.");
    expect(invalidateSpy).not.toHaveBeenCalled();
  });

  it("does nothing when there is no conversation id yet", () => {
    const { result } = renderHookWithClient(() => useSendMessageStream(undefined));

    act(() => {
      result.current.send("Hello?");
    });

    expect(mockedConversationsApi.streamMessage).not.toHaveBeenCalled();
    expect(result.current.status).toBe("idle");
  });
});
