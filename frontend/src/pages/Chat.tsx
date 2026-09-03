import { useState } from "react";
import { FileText, MessagesSquare, Pencil } from "lucide-react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { DocumentScopeDialog } from "@/components/chat/DocumentScopeDialog";
import { EmptyState } from "@/components/common/EmptyState";
import { useConversationQuery, useUpdateConversationDocumentsMutation } from "@/hooks/useConversations";
import { useDocumentsQuery } from "@/hooks/useDocuments";

export function Chat() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const { data: conversation, isLoading } = useConversationQuery(conversationId);
  const { data: documentsData } = useDocumentsQuery();
  const updateDocuments = useUpdateConversationDocumentsMutation();
  const [scopeDialogOpen, setScopeDialogOpen] = useState(false);

  if (!conversationId) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <EmptyState
          icon={MessagesSquare}
          title="No conversation selected"
          description="Start a new chat from the sidebar to begin asking questions."
        />
      </div>
    );
  }

  if (isLoading || !conversation) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading conversation…</p>
      </div>
    );
  }

  const documentsById = new Map((documentsData?.documents ?? []).map((doc) => [doc.id, doc]));
  const scopedFilenames = conversation.document_ids
    .map((id) => documentsById.get(id)?.original_filename)
    .filter((name): name is string => Boolean(name));

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3.5 sm:px-6">
        <div className="min-w-0">
          <h1 className="truncate text-[15px] font-semibold tracking-tight">{conversation.title}</h1>
          <p className="mt-0.5 flex flex-wrap items-center gap-1 text-xs text-muted-foreground">
            <FileText className="h-3 w-3 shrink-0" aria-hidden="true" />
            {scopedFilenames.length === 0
              ? "All documents"
              : scopedFilenames.length <= 2
                ? scopedFilenames.join(", ")
                : `${scopedFilenames.length} documents selected`}
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={() => setScopeDialogOpen(true)}>
          <Pencil className="h-3.5 w-3.5" />
          Documents
        </Button>
      </div>

      <div className="min-h-0 flex-1">
        <ChatWindow conversationId={conversationId} />
      </div>

      <DocumentScopeDialog
        open={scopeDialogOpen}
        onOpenChange={setScopeDialogOpen}
        initialSelectedIds={conversation.document_ids}
        isSaving={updateDocuments.isPending}
        onSave={(ids) => {
          updateDocuments.mutate(
            { id: conversationId, documentIds: ids },
            {
              onSuccess: () => {
                setScopeDialogOpen(false);
                toast.success("Document scope updated.");
              },
              onError: (error) => toast.error(error.message || "Failed to update documents."),
            }
          );
        }}
      />
    </div>
  );
}
