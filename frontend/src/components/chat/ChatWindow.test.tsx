import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChatWindow } from "@/components/chat/ChatWindow";
import { useMessagesQuery, useSendMessageStream } from "@/hooks/useConversations";
import type { Message } from "@/types";

// Mocked at the hook level (not the underlying API/QueryClient) — ChatWindow
// is a container that just consumes these two hooks, so that's the natural
// seam for a component test: it isolates ChatWindow's own rendering/event
// logic from TanStack Query's plumbing, which the hook tests already cover.
vi.mock("@/hooks/useConversations", () => ({
  useMessagesQuery: vi.fn(),
  useSendMessageStream: vi.fn(),
}));

const mockedUseMessagesQuery = vi.mocked(useMessagesQuery);
const mockedUseSendMessageStream = vi.mocked(useSendMessageStream);

function makeMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: "msg-1",
    conversation_id: "conv-1",
    role: "user",
    content: "Hello?",
    sources: [],
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

function mockHooks({
  messages = [],
  send = vi.fn(),
  status = "idle",
  userContent = "",
  assistantText = "",
  errorMessage = null,
}: {
  messages?: Message[];
  send?: ReturnType<typeof vi.fn>;
  status?: "idle" | "streaming" | "error";
  userContent?: string;
  assistantText?: string;
  errorMessage?: string | null;
} = {}) {
  mockedUseMessagesQuery.mockReturnValue({
    data: { messages },
    isLoading: false,
  } as ReturnType<typeof useMessagesQuery>);
  mockedUseSendMessageStream.mockReturnValue({
    status,
    userContent,
    assistantText,
    errorMessage,
    send,
  } as unknown as ReturnType<typeof useSendMessageStream>);
  return { send };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ChatWindow suggested questions", () => {
  it("shows suggested question chips when the conversation has no messages yet", () => {
    mockHooks({ messages: [] });
    render(<ChatWindow conversationId="conv-1" />, { wrapper: MemoryRouter });

    expect(screen.getByRole("button", { name: "What is this document about?" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "What are the main concepts?" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Summarize the key points." })).toBeInTheDocument();
  });

  it("sends the suggested question directly when clicked", () => {
    const { send } = mockHooks({ messages: [] });
    render(<ChatWindow conversationId="conv-1" />, { wrapper: MemoryRouter });

    fireEvent.click(screen.getByRole("button", { name: "Summarize the key points." }));

    expect(send).toHaveBeenCalledWith("Summarize the key points.");
  });

  it("disables suggestions while a message is already sending", () => {
    mockHooks({ messages: [], status: "streaming" });
    render(<ChatWindow conversationId="conv-1" />, { wrapper: MemoryRouter });

    expect(screen.getByRole("button", { name: "What is this document about?" })).toBeDisabled();
  });

  it("does not show suggestions once the conversation has messages", () => {
    mockHooks({ messages: [makeMessage()] });
    render(<ChatWindow conversationId="conv-1" />, { wrapper: MemoryRouter });

    expect(
      screen.queryByRole("button", { name: "What is this document about?" })
    ).not.toBeInTheDocument();
  });
});

describe("ChatWindow streaming", () => {
  it("shows the optimistic question and a thinking indicator before any text arrives", () => {
    mockHooks({ messages: [], status: "streaming", userContent: "What is RPC?" });
    render(<ChatWindow conversationId="conv-1" />, { wrapper: MemoryRouter });

    expect(screen.getByText("What is RPC?")).toBeInTheDocument();
    expect(screen.getByText("Thinking…")).toBeInTheDocument();
  });

  it("renders the answer text as it streams in", () => {
    mockHooks({
      messages: [],
      status: "streaming",
      userContent: "What is RPC?",
      assistantText: "RPC allows a client to",
    });
    render(<ChatWindow conversationId="conv-1" />, { wrapper: MemoryRouter });

    expect(screen.getByText("RPC allows a client to")).toBeInTheDocument();
    expect(screen.queryByText("Thinking…")).not.toBeInTheDocument();
  });

  it("shows an error message with a retry button that resends the original question", () => {
    const { send } = mockHooks({
      messages: [],
      status: "error",
      userContent: "What is RPC?",
      errorMessage: "The AI service is currently unavailable.",
    });
    render(<ChatWindow conversationId="conv-1" />, { wrapper: MemoryRouter });

    expect(screen.getByText("The AI service is currently unavailable.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(send).toHaveBeenCalledWith("What is RPC?");
  });
});
