import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MessageBubble } from "@/components/chat/MessageBubble";
import type { Message } from "@/types";

function baseMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: "m1",
    conversation_id: "c1",
    role: "assistant",
    content: "RPC allows a client to invoke a remote procedure.",
    sources: [],
    created_at: new Date().toISOString(),
    ...overrides,
  };
}

beforeEach(() => {
  Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } });
});

describe("MessageBubble", () => {
  it("renders a user message without a Sources section", () => {
    render(<MessageBubble message={baseMessage({ role: "user", content: "What is RPC?" })} />, {
      wrapper: MemoryRouter,
    });
    expect(screen.getByText("What is RPC?")).toBeInTheDocument();
    expect(screen.queryByText("Sources")).not.toBeInTheDocument();
  });

  it("renders assistant markdown content", () => {
    render(
      <MessageBubble message={baseMessage({ content: "**RPC** allows remote calls." })} />,
      { wrapper: MemoryRouter }
    );
    expect(screen.getByText("RPC")).toBeInTheDocument();
    expect(screen.getByText("RPC").tagName).toBe("STRONG");
  });

  it("renders source cards for an assistant message with citations", () => {
    render(
      <MessageBubble
        message={baseMessage({
          sources: [
            {
              chunk_id: "c1",
              document_id: "d1",
              filename: "notes.pdf",
              page_number: 12,
              similarity_score: 0.8,
            },
          ],
        })}
      />,
      { wrapper: MemoryRouter }
    );
    expect(screen.getByText("Sources")).toBeInTheDocument();
    expect(screen.getByText("notes.pdf")).toBeInTheDocument();
  });

  it("does not render a Sources section when there are no citations", () => {
    render(<MessageBubble message={baseMessage({ sources: [] })} />, { wrapper: MemoryRouter });
    expect(screen.queryByText("Sources")).not.toBeInTheDocument();
  });
});
