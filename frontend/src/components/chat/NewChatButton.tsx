import { useState } from "react";
import { MessageSquarePlus } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { Button, type ButtonProps } from "@/components/ui/button";
import { DocumentScopeDialog } from "@/components/chat/DocumentScopeDialog";
import { useCreateConversationMutation } from "@/hooks/useConversations";

interface NewChatButtonProps {
  variant?: ButtonProps["variant"];
  size?: ButtonProps["size"];
  className?: string;
}

/**
 * Starting a new chat used to always scope it to every document, leaving
 * document selection as something you only did afterwards (via the
 * "Documents" button in the chat header). This asks upfront instead, reusing
 * the same picker dialog that conversation already uses to change its scope.
 */
export function NewChatButton({ variant = "default", size = "sm", className }: NewChatButtonProps) {
  const navigate = useNavigate();
  const createConversation = useCreateConversationMutation();
  const [pickerOpen, setPickerOpen] = useState(false);

  function handleStart(documentIds: string[]) {
    createConversation.mutate(
      { documentIds },
      {
        onSuccess: (conversation) => {
          setPickerOpen(false);
          navigate(`/chat/${conversation.id}`);
        },
        onError: (error) => toast.error(error.message || "Failed to start a new chat."),
      }
    );
  }

  return (
    <>
      <Button
        type="button"
        variant={variant}
        size={size}
        className={className}
        onClick={() => setPickerOpen(true)}
      >
        <MessageSquarePlus className="h-4 w-4" />
        New Chat
      </Button>

      <DocumentScopeDialog
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        initialSelectedIds={[]}
        title="Start a new chat"
        description="Choose which documents to search, or leave nothing selected to search all of your documents."
        confirmLabel="Start Chat"
        savingLabel="Starting…"
        isSaving={createConversation.isPending}
        onSave={handleStart}
      />
    </>
  );
}
