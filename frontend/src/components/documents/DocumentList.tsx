import { useState } from "react";
import { FileText } from "lucide-react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { EmptyState } from "@/components/common/EmptyState";
import { SearchInput } from "@/components/common/SearchInput";
import { DocumentListItem } from "@/components/documents/DocumentListItem";
import { UploadDropzone } from "@/components/documents/UploadDropzone";
import { useDeleteDocumentMutation, useDocumentsQuery, useMultiFileUpload } from "@/hooks/useDocuments";
import type { DocChatDocument } from "@/types";

// Below this count the list is short enough to just scan by eye — showing a
// search box then would be more clutter than it saves.
const SEARCH_THRESHOLD = 5;

export function filterDocuments(documents: DocChatDocument[], query: string): DocChatDocument[] {
  const trimmed = query.trim().toLowerCase();
  if (!trimmed) return documents;
  return documents.filter((document) => document.original_filename.toLowerCase().includes(trimmed));
}

interface DocumentListProps {
  selectable?: boolean;
  selectedIds?: string[];
  onToggleSelect?: (id: string) => void;
}

export function DocumentList({ selectable, selectedIds = [], onToggleSelect }: DocumentListProps) {
  const { data, isLoading } = useDocumentsQuery();
  const { uploadFiles, isUploading } = useMultiFileUpload();
  const deleteMutation = useDeleteDocumentMutation();
  const [pendingDelete, setPendingDelete] = useState<DocChatDocument | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const documents = data?.documents ?? [];
  const showSearch = documents.length > SEARCH_THRESHOLD;
  const visibleDocuments = showSearch ? filterDocuments(documents, searchQuery) : documents;

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
      <UploadDropzone onUpload={uploadFiles} isUploading={isUploading} />

      {showSearch && (
        <SearchInput
          value={searchQuery}
          onChange={setSearchQuery}
          placeholder="Search documents…"
          aria-label="Search documents"
        />
      )}

      {isLoading ? (
        <p className="px-2 text-sm text-muted-foreground">Loading documents…</p>
      ) : documents.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No documents yet"
          description="Upload a PDF to start chatting with your documents."
        />
      ) : visibleDocuments.length === 0 ? (
        <p className="px-2 text-sm text-muted-foreground">No documents match "{searchQuery.trim()}".</p>
      ) : (
        <ul className="flex flex-col gap-0.5" aria-label="Uploaded documents">
          {visibleDocuments.map((document) => (
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
