import { describe, expect, it } from "vitest";

import { filterDocuments } from "@/components/documents/DocumentList";
import type { DocChatDocument } from "@/types";

function makeDocument(overrides: Partial<DocChatDocument>): DocChatDocument {
  return {
    id: "doc-1",
    filename: "notes.pdf",
    original_filename: "notes.pdf",
    status: "READY",
    file_size: 1024,
    page_count: 1,
    chunk_count: 1,
    error_message: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

describe("filterDocuments", () => {
  const documents = [
    makeDocument({ id: "1", original_filename: "Quarterly Report.pdf" }),
    makeDocument({ id: "2", original_filename: "resume.pdf" }),
    makeDocument({ id: "3", original_filename: "Meeting Notes.pdf" }),
  ];

  it("returns all documents when the query is empty", () => {
    expect(filterDocuments(documents, "")).toEqual(documents);
  });

  it("returns all documents when the query is only whitespace", () => {
    expect(filterDocuments(documents, "   ")).toEqual(documents);
  });

  it("filters case-insensitively by filename substring", () => {
    expect(filterDocuments(documents, "report").map((d) => d.id)).toEqual(["1"]);
    expect(filterDocuments(documents, "NOTES").map((d) => d.id)).toEqual(["3"]);
  });

  it("returns an empty array when nothing matches", () => {
    expect(filterDocuments(documents, "nonexistent")).toEqual([]);
  });

  it("trims surrounding whitespace from the query", () => {
    expect(filterDocuments(documents, "  resume  ").map((d) => d.id)).toEqual(["2"]);
  });
});
