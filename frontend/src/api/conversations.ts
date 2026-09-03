import { apiClient } from "@/api/client";
import type { Conversation, ConversationListResponse, Message, MessageListResponse } from "@/types";

export const conversationsApi = {
  list: () => apiClient.get<ConversationListResponse>("/conversations"),

  get: (id: string) => apiClient.get<Conversation>(`/conversations/${id}`),

  create: (documentIds: string[] = [], title?: string) =>
    apiClient.post<Conversation>("/conversations", { document_ids: documentIds, title }),

  rename: (id: string, title: string) =>
    apiClient.patch<Conversation>(`/conversations/${id}`, { title }),

  updateDocuments: (id: string, documentIds: string[]) =>
    apiClient.patch<Conversation>(`/conversations/${id}`, { document_ids: documentIds }),

  remove: (id: string) => apiClient.delete<void>(`/conversations/${id}`),

  listMessages: (id: string) => apiClient.get<MessageListResponse>(`/conversations/${id}/messages`),

  sendMessage: (id: string, content: string) =>
    apiClient.post<Message>(`/conversations/${id}/messages`, { content }),
};
