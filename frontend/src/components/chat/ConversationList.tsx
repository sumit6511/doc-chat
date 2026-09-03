import { useState } from "react";
import { MessageSquarePlus, MessagesSquare, Pencil, Trash2 } from "lucide-react";
import { NavLink } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { EmptyState } from "@/components/common/EmptyState";
import {
  useConversationsQuery,
  useDeleteConversationMutation,
  useRenameConversationMutation,
} from "@/hooks/useConversations";
import { cn, formatRelativeTime } from "@/lib/utils";
import type { Conversation } from "@/types";

export function ConversationList({ onCreateNew }: { onCreateNew: () => void }) {
  const { data, isLoading } = useConversationsQuery();
  const renameMutation = useRenameConversationMutation();
  const deleteMutation = useDeleteConversationMutation();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [pendingDelete, setPendingDelete] = useState<Conversation | null>(null);

  const conversations = data?.conversations ?? [];

  function startRename(conversation: Conversation) {
    setEditingId(conversation.id);
    setDraftTitle(conversation.title);
  }

  function commitRename(id: string) {
    const title = draftTitle.trim();
    setEditingId(null);
    if (!title) return;
    renameMutation.mutate(
      { id, title },
      { onError: (error) => toast.error(error.message || "Failed to rename conversation.") }
    );
  }

  function handleConfirmDelete() {
    if (!pendingDelete) return;
    deleteMutation.mutate(pendingDelete.id, {
      onSuccess: () => setPendingDelete(null),
      onError: (error) => toast.error(error.message || "Failed to delete conversation."),
    });
  }

  return (
    <div className="flex flex-col gap-2">
      <Button type="button" size="sm" className="w-full justify-start" onClick={onCreateNew}>
        <MessageSquarePlus className="h-4 w-4" />
        New Chat
      </Button>

      {isLoading ? (
        <p className="px-2 text-sm text-muted-foreground">Loading conversations…</p>
      ) : conversations.length === 0 ? (
        <EmptyState
          icon={MessagesSquare}
          title="No conversations yet"
          description="Choose a document and start asking questions."
        />
      ) : (
        <ul className="flex flex-col gap-0.5" aria-label="Conversations">
          {conversations.map((conversation) => (
            <li key={conversation.id} className="group">
              {editingId === conversation.id ? (
                <Input
                  autoFocus
                  value={draftTitle}
                  onChange={(e) => setDraftTitle(e.target.value)}
                  onBlur={() => commitRename(conversation.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") commitRename(conversation.id);
                    if (e.key === "Escape") setEditingId(null);
                  }}
                  className="h-8"
                />
              ) : (
                <NavLink
                  to={`/chat/${conversation.id}`}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-2 rounded-lg px-2 py-2.5 text-sm transition-colors hover:bg-accent",
                      isActive && "bg-accent font-medium"
                    )
                  }
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate">{conversation.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {conversation.message_count} message{conversation.message_count === 1 ? "" : "s"} ·{" "}
                      {formatRelativeTime(conversation.updated_at)}
                    </p>
                  </div>
                  <span className="flex shrink-0 gap-0.5 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={(e) => {
                        e.preventDefault();
                        startRename(conversation);
                      }}
                      aria-label={`Rename ${conversation.title}`}
                    >
                      <Pencil className="h-3 w-3" />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={(e) => {
                        e.preventDefault();
                        setPendingDelete(conversation);
                      }}
                      aria-label={`Delete ${conversation.title}`}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </span>
                </NavLink>
              )}
            </li>
          ))}
        </ul>
      )}

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onOpenChange={(open) => !open && setPendingDelete(null)}
        title="Delete conversation?"
        description={
          <>
            This permanently deletes <strong>{pendingDelete?.title}</strong> and all of its
            messages. This can't be undone.
          </>
        }
        isConfirming={deleteMutation.isPending}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
}
