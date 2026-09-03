import { render, screen } from "@testing-library/react";
import { FileText } from "lucide-react";
import { describe, expect, it } from "vitest";

import { EmptyState } from "@/components/common/EmptyState";

describe("EmptyState", () => {
  it("renders the title and description", () => {
    render(
      <EmptyState
        icon={FileText}
        title="No documents yet"
        description="Upload a PDF to start chatting with your documents."
      />
    );
    expect(screen.getByText("No documents yet")).toBeInTheDocument();
    expect(
      screen.getByText("Upload a PDF to start chatting with your documents.")
    ).toBeInTheDocument();
  });

  it("renders an optional action", () => {
    render(
      <EmptyState icon={FileText} title="No documents yet" action={<button>Upload PDF</button>} />
    );
    expect(screen.getByRole("button", { name: "Upload PDF" })).toBeInTheDocument();
  });
});
