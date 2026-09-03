import { useCallback, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { conversationsApi } from "@/api/conversations";

export const conversationsKey = ["conversations"] as const;
export const conversationKey = (id: string) => ["conversations", id] as const;
export const messagesKey = (id: string) => ["conversations", id, "messages"] as const;

export function useConversationsQuery() {
  return useQuery({
    queryKey: conversationsKey,
    queryFn: conversationsApi.list,
  });
}

export function useConversationQuery(conversationId: string | undefined) {
  return useQuery({
    queryKey: conversationId ? conversationKey(conversationId) : conversationsKey,
    queryFn: () => conversationsApi.get(conversationId as string),
    enabled: Boolean(conversationId),
  });
}

export function useCreateConversationMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ documentIds, title }: { documentIds?: string[]; title?: string }) =>
      conversationsApi.create(documentIds, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: conversationsKey });
    },
  });
}

export function useRenameConversationMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      conversationsApi.rename(id, title),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: conversationsKey });
      queryClient.invalidateQueries({ queryKey: conversationKey(variables.id) });
    },
  });
}

export function useUpdateConversationDocumentsMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, documentIds }: { id: string; documentIds: string[] }) =>
      conversationsApi.updateDocuments(id, documentIds),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: conversationsKey });
      queryClient.invalidateQueries({ queryKey: conversationKey(variables.id) });
    },
  });
}

export function useDeleteConversationMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => conversationsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: conversationsKey });
    },
  });
}

export function useMessagesQuery(conversationId: string | undefined) {
  return useQuery({
    queryKey: conversationId ? messagesKey(conversationId) : ["messages"],
    queryFn: () => conversationsApi.listMessages(conversationId as string),
    enabled: Boolean(conversationId),
  });
}

export interface StreamingChatState {
  status: "idle" | "streaming" | "error";
  /** The question currently in flight (kept through "error" so a retry has something to resend). */
  userContent: string;
  /** Accumulated answer text so far — empty until the first token arrives. */
  assistantText: string;
  errorMessage: string | null;
}

const idleStreamingState: StreamingChatState = {
  status: "idle",
  userContent: "",
  assistantText: "",
  errorMessage: null,
};

export function useSendMessageStream(conversationId: string | undefined) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<StreamingChatState>(idleStreamingState);

  const send = useCallback(
    (content: string) => {
      if (!conversationId) return;

      setState({ status: "streaming", userContent: content, assistantText: "", errorMessage: null });

      void (async () => {
        try {
          for await (const event of conversationsApi.streamMessage(conversationId, content)) {
            if (event.type === "delta") {
              setState((prev) => ({ ...prev, assistantText: prev.assistantText + event.text }));
            } else if (event.type === "error") {
              setState((prev) => ({ ...prev, status: "error", errorMessage: event.message }));
              return;
            } else {
              // "done" — the canonical messages now live server-side; refetch
              // before clearing the optimistic bubbles so nothing disappears
              // and reappears.
              await Promise.all([
                queryClient.invalidateQueries({ queryKey: messagesKey(conversationId) }),
                queryClient.invalidateQueries({ queryKey: conversationsKey }),
                queryClient.invalidateQueries({ queryKey: conversationKey(conversationId) }),
              ]);
              setState(idleStreamingState);
              return;
            }
          }
        } catch (error) {
          setState((prev) => ({
            ...prev,
            status: "error",
            errorMessage: error instanceof Error ? error.message : "Something went wrong.",
          }));
        }
      })();
    },
    [conversationId, queryClient]
  );

  return { ...state, send };
}
