import { useState } from "react";
import { FileText } from "lucide-react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { EmptyState } from "@/components/common/EmptyState";
import { DocumentListItem } from "@/components/documents/DocumentListItem";
import { UploadDropzone } from "@/components/documents/UploadDropzone";
import { useDeleteDocumentMutation, useDocumentsQuery, useUploadDocumentMutation } from "@/hooks/useDocuments";
import type { DocChatDocument } from "@/types";

interface DocumentListProps {
  selectable?: boolean;
  selectedIds?: string[];
  onToggleSelect?: (id: string) => void;
}

export function DocumentList({ selectable, selectedIds = [], onToggleSelect }: DocumentListProps) {
  const { data, isLoading } = useDocumentsQuery();
  const uploadMutation = useUploadDocumentMutation();
  const deleteMutation = useDeleteDocumentMutation();
  const [pendingDelete, setPendingDelete] = useState<DocChatDocument | null>(null);

  const documents = data?.documents ?? [];

  function handleUpload(file: File) {
    uploadMutation.mutate(file, {
      onError: (error) => toast.error(error.message || "Upload failed."),
      onSuccess: () => toast.success(`${file.name} uploaded — processing started.`),
    });
  }

  function handleConfirmDelete() {
    if (!pendingDelete) return;
    deleteMutation.mutate(pendingDelete.id, {
      onSuccess: () => {
        toast.success(`${pendingDelete.original_filename} deleted.`);
        setPendingDelete(null);
      },
      onError: (error) => toast.error(error.message || "Failed to delete document."),
    });
  }

  return (
    <div className="flex flex-col gap-3">
      <UploadDropzone onUpload={handleUpload} isUploading={uploadMutation.isPending} />

      {isLoading ? (
        <p className="px-2 text-sm text-muted-foreground">Loading documents…</p>
      ) : documents.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No documents yet"
          description="Upload a PDF to start chatting with your documents."
        />
      ) : (
        <ul className="flex flex-col gap-0.5" aria-label="Uploaded documents">
          {documents.map((document) => (
            <li key={document.id}>
              <DocumentListItem
                document={document}
                selectable={selectable}
                selected={selectedIds.includes(document.id)}
                onToggleSelect={onToggleSelect}
                onDelete={() => setPendingDelete(document)}
              />
            </li>
          ))}
        </ul>
      )}

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onOpenChange={(open) => !open && setPendingDelete(null)}
        title="Delete document?"
        description={
          <>
            This permanently deletes <strong>{pendingDelete?.original_filename}</strong> and all of
            its indexed chunks. Conversations referencing it will lose that context. This can't be
            undone.
          </>
        }
        isConfirming={deleteMutation.isPending}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
}
