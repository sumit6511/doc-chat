import { describe, expect, it } from "vitest";

import { filterConversations } from "@/components/chat/ConversationList";
import type { Conversation } from "@/types";

function makeConversation(overrides: Partial<Conversation>): Conversation {
  return {
    id: "conv-1",
    title: "Untitled conversation",
    document_ids: [],
    message_count: 0,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

describe("filterConversations", () => {
  const conversations = [
    makeConversation({ id: "1", title: "Quarterly Report Review" }),
    makeConversation({ id: "2", title: "Resume feedback" }),
    makeConversation({ id: "3", title: "Meeting Notes Summary" }),
  ];

  it("returns all conversations when the query is empty", () => {
    expect(filterConversations(conversations, "")).toEqual(conversations);
  });

  it("returns all conversations when the query is only whitespace", () => {
    expect(filterConversations(conversations, "   ")).toEqual(conversations);
  });

  it("filters case-insensitively by title substring", () => {
    expect(filterConversations(conversations, "report").map((c) => c.id)).toEqual(["1"]);
    expect(filterConversations(conversations, "NOTES").map((c) => c.id)).toEqual(["3"]);
  });

  it("returns an empty array when nothing matches", () => {
    expect(filterConversations(conversations, "nonexistent")).toEqual([]);
  });

  it("trims surrounding whitespace from the query", () => {
    expect(filterConversations(conversations, "  resume  ").map((c) => c.id)).toEqual(["2"]);
  });
});
