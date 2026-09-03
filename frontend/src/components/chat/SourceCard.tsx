import { FileText } from "lucide-react";
import { Link } from "react-router-dom";

import { formatRelevancePercent } from "@/lib/utils";
import type { SourceCitation } from "@/types";

export function SourceCard({ source }: { source: SourceCitation }) {
  return (
    <Link
      to={`/documents/${source.document_id}?page=${source.page_number}`}
      className="flex items-start gap-2 rounded-lg border border-border bg-card px-3 py-2 text-xs transition-colors hover:border-primary/40 hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
      <span className="min-w-0">
        <span className="block truncate font-medium text-foreground" title={source.filename}>
          {source.filename}
        </span>
        <span className="text-muted-foreground">
          Page {source.page_number} · Relevance {formatRelevancePercent(source.similarity_score)}
        </span>
      </span>
    </Link>
  );
}
