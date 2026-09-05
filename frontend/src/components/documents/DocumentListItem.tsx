import { FileText, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/documents/StatusBadge";
import { cn, formatFileSize } from "@/lib/utils";
import type { DocChatDocument } from "@/types";

interface DocumentListItemProps {
  document: DocChatDocument;
  selected?: boolean;
  onToggleSelect?: (id: string) => void;
  onDelete?: (id: string) => void;
  selectable?: boolean;
}

export function DocumentListItem({
  document,
  selected,
  onToggleSelect,
  onDelete,
  selectable,
}: DocumentListItemProps) {
  return (
    <div
      className={cn(
        "group flex items-start gap-2 rounded-lg px-2 py-2.5 text-sm transition-colors hover:bg-accent",
        selected && "bg-accent"
      )}
    >
      {selectable && (
        <input
          type="checkbox"
          className="mt-1 h-3.5 w-3.5 shrink-0 rounded border-input accent-primary"
          checked={Boolean(selected)}
          onChange={() => onToggleSelect?.(document.id)}
          aria-label={`Select ${document.original_filename} for this conversation`}
        />
      )}
      <FileText className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <Link
          to={`/documents/${document.id}`}
          className="block truncate font-medium text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm"
          title={document.original_filename}
        >
          {document.original_filename}
        </Link>
        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          <StatusBadge status={document.status} />
          <span className="text-xs text-muted-foreground">{formatFileSize(document.file_size)}</span>
          {document.page_count != null && (
            <span className="text-xs text-muted-foreground">· {document.page_count}p</span>
          )}
        </div>
        {document.status === "FAILED" && document.error_message && (
          <p className="mt-1 text-xs text-destructive">{document.error_message}</p>
        )}
      </div>
      {onDelete && (
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0 self-center opacity-0 group-hover:opacity-100 group-focus-within:opacity-100"
          onClick={() => onDelete(document.id)}
          aria-label={`Delete ${document.original_filename}`}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      )}
    </div>
  );
}
