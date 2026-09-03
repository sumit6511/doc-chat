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

export function useSendMessageMutation(conversationId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (content: string) => conversationsApi.sendMessage(conversationId as string, content),
    onSuccess: () => {
      if (!conversationId) return;
      queryClient.invalidateQueries({ queryKey: messagesKey(conversationId) });
      queryClient.invalidateQueries({ queryKey: conversationsKey });
      queryClient.invalidateQueries({ queryKey: conversationKey(conversationId) });
    },
  });
}
