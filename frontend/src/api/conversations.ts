import { apiClient, API_BASE_URL, parseErrorResponse } from "@/api/client";
import type {
  Conversation,
  ConversationListResponse,
  MessageListResponse,
  StreamEvent,
} from "@/types";

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

  /**
   * Posts a question and streams the answer back as Server-Sent Events
   * rather than waiting for the full response. `fetch`'s ReadableStream is
   * used directly instead of EventSource, since EventSource can't send a
   * POST body.
   */
  async *streamMessage(id: string, content: string, signal?: AbortSignal): AsyncGenerator<StreamEvent> {
    const response = await fetch(`${API_BASE_URL}/conversations/${id}/messages/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ content }),
      signal,
    });

    if (!response.ok || !response.body) {
      throw await parseErrorResponse(response);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let separatorIndex: number;
      while ((separatorIndex = buffer.indexOf("\n\n")) !== -1) {
        const rawEvent = buffer.slice(0, separatorIndex);
        buffer = buffer.slice(separatorIndex + 2);
        const dataLine = rawEvent.split("\n").find((line) => line.startsWith("data: "));
        if (dataLine) {
          yield JSON.parse(dataLine.slice("data: ".length)) as StreamEvent;
        }
      }
    }
  },
};
