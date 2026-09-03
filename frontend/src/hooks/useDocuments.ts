import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { documentsApi } from "@/api/documents";
import type { DocumentListResponse } from "@/types";

const documentsKey = ["documents"] as const;

const ACTIVE_STATUSES = new Set(["UPLOADING", "PROCESSING"]);

export function useDocumentsQuery() {
  return useQuery({
    queryKey: documentsKey,
    queryFn: documentsApi.list,
    // Poll while anything is still processing so status badges and the
    // dashboard page-count update without a manual refresh; stop once every
    // document has reached a terminal state (READY or FAILED).
    refetchInterval: (query) => {
      const data = query.state.data as DocumentListResponse | undefined;
      const stillProcessing = data?.documents.some((doc) => ACTIVE_STATUSES.has(doc.status));
      return stillProcessing ? 2500 : false;
    },
  });
}

export function useUploadDocumentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => documentsApi.upload(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentsKey });
    },
  });
}

export function useDeleteDocumentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => documentsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentsKey });
    },
  });
}
