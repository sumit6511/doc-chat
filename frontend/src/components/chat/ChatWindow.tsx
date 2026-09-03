import { useEffect, useRef, useState } from "react";
import { MessagesSquare, RotateCcw, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/EmptyState";
import { Spinner } from "@/components/common/Spinner";
import { ChatInput } from "@/components/chat/ChatInput";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { useMessagesQuery, useSendMessageMutation } from "@/hooks/useConversations";

// Deliberately static rather than LLM-generated: these three work as a
// starting point for any document, and generating per-document suggestions
// would mean an extra LLM round trip for a feature that's meant to be a
// small nicety, not another part of the core RAG pipeline.
const SUGGESTED_QUESTIONS = [
  "What is this document about?",
  "What are the main concepts?",
  "Summarize the key points.",
];

export function ChatWindow({ conversationId }: { conversationId: string }) {
  const { data, isLoading } = useMessagesQuery(conversationId);
  const sendMessage = useSendMessageMutation(conversationId);
  const [draft, setDraft] = useState("");
  const [lastFailedContent, setLastFailedContent] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const messages = data?.messages ?? [];

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages.length, sendMessage.isPending]);

  function handleSend(content?: string) {
    const text = (content ?? draft).trim();
    if (!text) return;
    setDraft("");
    setLastFailedContent(null);
    sendMessage.mutate(text, {
      onError: () => setLastFailedContent(text),
    });
  }

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin px-4 py-6 sm:px-6">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading conversation…</p>
        ) : messages.length === 0 ? (
          <EmptyState
            icon={MessagesSquare}
            title="Ask your first question"
            description="DocChat will search your documents and answer with citations."
            action={
              <div className="flex flex-col items-center gap-2 pt-1">
                <p className="text-xs text-muted-foreground">Or try asking:</p>
                <div className="flex flex-wrap justify-center gap-2">
                  {SUGGESTED_QUESTIONS.map((question) => (
                    <Button
                      key={question}
                      type="button"
                      variant="outline"
                      size="sm"
                      className="rounded-full"
                      disabled={sendMessage.isPending}
                      onClick={() => handleSend(question)}
                    >
                      {question}
                    </Button>
                  ))}
                </div>
              </div>
            }
          />
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-7">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
          </div>
        )}

        {sendMessage.isPending && (
          <div className="mx-auto mt-7 flex max-w-3xl animate-fade-in items-center gap-3">
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10">
              <Sparkles className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Spinner label="DocChat is thinking" />
              Thinking…
            </div>
          </div>
        )}

        {lastFailedContent && (
          <div className="mx-auto mt-7 flex max-w-3xl flex-col items-start gap-2 rounded-xl border border-destructive/30 bg-destructive/5 p-3.5 text-sm">
            <p className="text-destructive">Something went wrong getting a response. Please try again.</p>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => handleSend(lastFailedContent)}
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Retry
            </Button>
          </div>
        )}
      </div>

      <ChatInput
        value={draft}
        onChange={setDraft}
        onSubmit={() => handleSend()}
        disabled={sendMessage.isPending}
      />
    </div>
  );
}
