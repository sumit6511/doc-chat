import { useNavigate } from "react-router-dom";

import { ConversationList } from "@/components/chat/ConversationList";
import { DocumentList } from "@/components/documents/DocumentList";
import { useCreateConversationMutation } from "@/hooks/useConversations";

export function Sidebar() {
  const navigate = useNavigate();
  const createConversation = useCreateConversationMutation();

  function handleCreateNew() {
    createConversation.mutate(
      { documentIds: [] },
      { onSuccess: (conversation) => navigate(`/chat/${conversation.id}`) }
    );
  }

  return (
    <nav className="flex h-full flex-col gap-7 overflow-y-auto scrollbar-thin p-3.5" aria-label="Documents and conversations">
      <section aria-labelledby="documents-heading">
        <h2 id="documents-heading" className="mb-2.5 px-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Documents
        </h2>
        <DocumentList />
      </section>

      <section aria-labelledby="conversations-heading">
        <h2 id="conversations-heading" className="mb-2.5 px-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Conversations
        </h2>
        <ConversationList onCreateNew={handleCreateNew} />
      </section>
    </nav>
  );
}
