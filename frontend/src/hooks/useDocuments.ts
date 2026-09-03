import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

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

/**
 * Fires one upload per file (the backend's /documents endpoint is
 * single-file, by design — this keeps each file's success/failure
 * independent) and reports progress/results per file. isUploading tracks a
 * local in-flight count rather than the underlying mutation's own
 * `isPending`, since one `useMutation` instance only reflects its most
 * recent call — not "is at least one of N concurrent uploads still running".
 */
export function useMultiFileUpload() {
  const uploadMutation = useUploadDocumentMutation();
  const [pendingCount, setPendingCount] = useState(0);

  function uploadFiles(files: File[]) {
    for (const file of files) {
      setPendingCount((count) => count + 1);
      uploadMutation.mutate(file, {
        onSuccess: () => toast.success(`${file.name} uploaded — processing started.`),
        onError: (error) => toast.error(`${file.name}: ${error.message || "Upload failed."}`),
        onSettled: () => setPendingCount((count) => count - 1),
      });
    }
  }

  return { uploadFiles, isUploading: pendingCount > 0 };
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
