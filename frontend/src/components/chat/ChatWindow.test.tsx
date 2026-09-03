import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChatWindow } from "@/components/chat/ChatWindow";
import { useMessagesQuery, useSendMessageMutation } from "@/hooks/useConversations";
import type { Message } from "@/types";

// Mocked at the hook level (not the underlying API/QueryClient) — ChatWindow
// is a container that just consumes these two hooks, so that's the natural
// seam for a component test: it isolates ChatWindow's own rendering/event
// logic from TanStack Query's plumbing, which the hook tests already cover.
vi.mock("@/hooks/useConversations", () => ({
  useMessagesQuery: vi.fn(),
  useSendMessageMutation: vi.fn(),
}));

const mockedUseMessagesQuery = vi.mocked(useMessagesQuery);
const mockedUseSendMessageMutation = vi.mocked(useSendMessageMutation);

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
  mutate = vi.fn(),
  isPending = false,
}: { messages?: Message[]; mutate?: ReturnType<typeof vi.fn>; isPending?: boolean } = {}) {
  mockedUseMessagesQuery.mockReturnValue({
    data: { messages },
    isLoading: false,
  } as ReturnType<typeof useMessagesQuery>);
  mockedUseSendMessageMutation.mockReturnValue({
    mutate,
    isPending,
  } as unknown as ReturnType<typeof useSendMessageMutation>);
  return { mutate };
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
    const { mutate } = mockHooks({ messages: [] });
    render(<ChatWindow conversationId="conv-1" />, { wrapper: MemoryRouter });

    fireEvent.click(screen.getByRole("button", { name: "Summarize the key points." }));

    expect(mutate).toHaveBeenCalledWith("Summarize the key points.", expect.anything());
  });

  it("disables suggestions while a message is already sending", () => {
    mockHooks({ messages: [], isPending: true });
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
