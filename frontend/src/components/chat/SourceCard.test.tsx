import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { SourceCard } from "@/components/chat/SourceCard";
import type { SourceCitation } from "@/types";

const source: SourceCitation = {
  chunk_id: "chunk-1",
  document_id: "doc-1",
  filename: "Distributed Systems.pdf",
  page_number: 42,
  similarity_score: 0.91,
};

describe("SourceCard", () => {
  it("shows the filename, page number, and relevance percentage", () => {
    render(<SourceCard source={source} />, { wrapper: MemoryRouter });

    expect(screen.getByText("Distributed Systems.pdf")).toBeInTheDocument();
    expect(screen.getByText(/page 42/i)).toBeInTheDocument();
    expect(screen.getByText(/91%/)).toBeInTheDocument();
  });

  it("links to the document viewer at the cited page", () => {
    render(<SourceCard source={source} />, { wrapper: MemoryRouter });
    expect(screen.getByRole("link")).toHaveAttribute("href", "/documents/doc-1?page=42");
  });

  it("does not expose internal database ids in the visible text", () => {
    render(<SourceCard source={source} />, { wrapper: MemoryRouter });
    expect(screen.queryByText("chunk-1")).not.toBeInTheDocument();
  });
});
