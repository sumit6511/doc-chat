import { useState } from "react";
import { ArrowLeft, Download, Trash2 } from "lucide-react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { StatusBadge } from "@/components/documents/StatusBadge";
import { documentsApi } from "@/api/documents";
import { useDeleteDocumentMutation, useDocumentsQuery } from "@/hooks/useDocuments";
import { formatFileSize, formatRelativeTime } from "@/lib/utils";

export function Document() {
  const { documentId } = useParams<{ documentId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { data } = useDocumentsQuery();
  const deleteMutation = useDeleteDocumentMutation();
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const document = data?.documents.find((doc) => doc.id === documentId);
  const page = searchParams.get("page");

  if (!document) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <p className="text-sm text-muted-foreground">Document not found, or still loading…</p>
      </div>
    );
  }

  const fileUrl = documentsApi.fileUrl(document.id);
  const viewerUrl = page ? `${fileUrl}#page=${page}` : fileUrl;

  function handleDelete() {
    if (!document) return;
    deleteMutation.mutate(document.id, {
      onSuccess: () => {
        toast.success(`${document.original_filename} deleted.`);
        navigate("/");
      },
      onError: (error) => toast.error(error.message || "Failed to delete document."),
    });
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3.5 sm:px-6">
        <div className="flex min-w-0 items-center gap-2">
          <Button type="button" variant="ghost" size="icon" onClick={() => navigate(-1)} aria-label="Go back">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="min-w-0">
            <h1 className="truncate text-[15px] font-semibold tracking-tight">{document.original_filename}</h1>
            <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <StatusBadge status={document.status} />
              <span>{formatFileSize(document.file_size)}</span>
              {document.page_count != null && <span>{document.page_count} pages</span>}
              {document.chunk_count != null && <span>{document.chunk_count} chunks indexed</span>}
              <span>Uploaded {formatRelativeTime(document.created_at)}</span>
            </div>
          </div>
        </div>

        <div className="flex shrink-0 gap-2">
          <Button type="button" variant="outline" size="sm" asChild>
            <Link to={fileUrl} target="_blank" rel="noreferrer">
              <Download className="h-3.5 w-3.5" />
              Download
            </Link>
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={() => setConfirmingDelete(true)}>
            <Trash2 className="h-3.5 w-3.5" />
            Delete
          </Button>
        </div>
      </div>

      {document.status === "FAILED" ? (
        <div className="flex flex-1 items-center justify-center p-6">
          <div className="max-w-sm text-center">
            <Badge variant="destructive" className="mb-2">
              Processing failed
            </Badge>
            <p className="text-sm text-muted-foreground">
              {document.error_message ?? "This document could not be processed."}
            </p>
          </div>
        </div>
      ) : (
        <iframe title={document.original_filename} src={viewerUrl} className="h-full w-full flex-1 bg-muted" />
      )}

      <ConfirmDialog
        open={confirmingDelete}
        onOpenChange={setConfirmingDelete}
        title="Delete document?"
        description={
          <>
            This permanently deletes <strong>{document.original_filename}</strong> and all of its
            indexed chunks. This can't be undone.
          </>
        }
        isConfirming={deleteMutation.isPending}
        onConfirm={handleDelete}
      />
    </div>
  );
}
