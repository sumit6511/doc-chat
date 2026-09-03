import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { documentsApi } from "@/api/documents";
import type { DocumentListResponse } from "@/types";

export const documentsKey = ["documents"] as const;

const ACTIVE_STATUSES = new Set(["UPLOADING", "PROCESSING"]);
const POLL_INTERVAL_MS = 2500;

// Poll while anything is still processing so status badges and the
// dashboard page-count update without a manual refresh; stop once every
// document has reached a terminal state (READY or FAILED). Extracted as a
// pure function so this decision can be unit tested directly, without
// having to drive TanStack Query's actual polling cycle.
export function getDocumentsRefetchInterval(
  data: DocumentListResponse | undefined
): number | false {
  const stillProcessing = data?.documents.some((doc) => ACTIVE_STATUSES.has(doc.status));
  return stillProcessing ? POLL_INTERVAL_MS : false;
}

export function useDocumentsQuery() {
  return useQuery({
    queryKey: documentsKey,
    queryFn: documentsApi.list,
    refetchInterval: (query) =>
      getDocumentsRefetchInterval(query.state.data as DocumentListResponse | undefined),
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
 *
 * Uses mutateAsync (not mutate's per-call onSuccess/onError/onSettled
 * options) deliberately: those per-call options are stored on the shared
 * mutation observer, so firing mutate() again for the next file before the
 * previous one settles can let the later call's callbacks silently replace
 * the earlier call's — losing its success/error toast and its pendingCount
 * decrement (isUploading then never returns to false). mutateAsync returns
 * an independent promise per call with no such shared state.
 */
export function useMultiFileUpload() {
  const uploadMutation = useUploadDocumentMutation();
  const [pendingCount, setPendingCount] = useState(0);

  function uploadFiles(files: File[]) {
    for (const file of files) {
      setPendingCount((count) => count + 1);
      uploadMutation
        .mutateAsync(file)
        .then(() => toast.success(`${file.name} uploaded — processing started.`))
        .catch((error: Error) => toast.error(`${file.name}: ${error.message || "Upload failed."}`))
        .finally(() => setPendingCount((count) => count - 1));
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
