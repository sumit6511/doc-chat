import { apiClient, API_BASE_URL } from "@/api/client";
import type { DocChatDocument, DocumentListResponse } from "@/types";

export const documentsApi = {
  list: () => apiClient.get<DocumentListResponse>("/documents"),

  get: (id: string) => apiClient.get<DocChatDocument>(`/documents/${id}`),

  upload: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiClient.post<DocChatDocument>("/documents", formData);
  },

  remove: (id: string) => apiClient.delete<void>(`/documents/${id}`),

  fileUrl: (id: string) => `${API_BASE_URL}/documents/${id}/file`,
};
