import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBadge } from "@/components/documents/StatusBadge";
import type { DocumentStatus } from "@/types";

describe("StatusBadge", () => {
  it.each([
    ["UPLOADING", "Uploading"],
    ["PROCESSING", "Processing"],
    ["READY", "Ready"],
    ["FAILED", "Failed"],
  ] satisfies [DocumentStatus, string][])("renders the label for %s", (status, label) => {
    render(<StatusBadge status={status} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("never relies on color alone: each status has distinct visible text", () => {
    const statuses: DocumentStatus[] = ["UPLOADING", "PROCESSING", "READY", "FAILED"];
    const labels = new Set(statuses.map((status) => {
      const { unmount } = render(<StatusBadge status={status} />);
      const label = screen.getByText(/uploading|processing|ready|failed/i).textContent;
      unmount();
      return label;
    }));
    expect(labels.size).toBe(statuses.length);
  });
});
