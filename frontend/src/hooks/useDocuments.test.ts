import { waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { documentsApi } from "@/api/documents";
import {
  documentsKey,
  getDocumentsRefetchInterval,
  useDeleteDocumentMutation,
  useDocumentsQuery,
  useMultiFileUpload,
} from "@/hooks/useDocuments";
import { createTestQueryClient, renderHookWithClient } from "@/test/queryTestUtils";
import type { DocChatDocument, DocumentListResponse, DocumentStatus } from "@/types";

vi.mock("@/api/documents", () => ({
  documentsApi: {
    list: vi.fn(),
    get: vi.fn(),
    upload: vi.fn(),
    remove: vi.fn(),
    fileUrl: vi.fn(),
  },
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const mockedDocumentsApi = vi.mocked(documentsApi);

function makeDocument(overrides: Partial<DocChatDocument> = {}): DocChatDocument {
  return {
    id: "doc-1",
    filename: "abc.pdf",
    original_filename: "abc.pdf",
    file_size: 1000,
    page_count: 1,
    chunk_count: 1,
    status: "READY",
    error_message: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

function makeFile(name: string): File {
  return new File(["content"], name, { type: "application/pdf" });
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useDocumentsQuery", () => {
  it("returns the document list from the API", async () => {
    const response: DocumentListResponse = { documents: [makeDocument()], total: 1 };
    mockedDocumentsApi.list.mockResolvedValue(response);

    const { result } = renderHookWithClient(() => useDocumentsQuery());

    await waitFor(() => expect(result.current.data).toEqual(response));
  });
});

describe("getDocumentsRefetchInterval", () => {
  const statuses: DocumentStatus[] = ["UPLOADING", "PROCESSING"];

  it.each(statuses)("polls every 2.5s while a document is %s", (status) => {
    const data: DocumentListResponse = { documents: [makeDocument({ status })], total: 1 };
    expect(getDocumentsRefetchInterval(data)).toBe(2500);
  });

  it("stops polling once every document is READY or FAILED", () => {
    const data: DocumentListResponse = {
      documents: [
        makeDocument({ id: "a", status: "READY" }),
        makeDocument({ id: "b", status: "FAILED" }),
      ],
      total: 2,
    };
    expect(getDocumentsRefetchInterval(data)).toBe(false);
  });

  it("does not poll when there is no data yet", () => {
    expect(getDocumentsRefetchInterval(undefined)).toBe(false);
  });

  it("does not poll an empty document list", () => {
    expect(getDocumentsRefetchInterval({ documents: [], total: 0 })).toBe(false);
  });
});

describe("useDeleteDocumentMutation", () => {
  it("calls documentsApi.remove with the document id and invalidates the list", async () => {
    mockedDocumentsApi.remove.mockResolvedValue(undefined);
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHookWithClient(() => useDeleteDocumentMutation(), { queryClient });

    result.current.mutate("doc-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedDocumentsApi.remove).toHaveBeenCalledWith("doc-1");
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: documentsKey });
  });
});

describe("useMultiFileUpload", () => {
  it("uploads each file independently and reports success per file", async () => {
    mockedDocumentsApi.upload.mockImplementation((file: File) =>
      Promise.resolve(makeDocument({ id: file.name, original_filename: file.name }))
    );

    const { result } = renderHookWithClient(() => useMultiFileUpload());
    const { toast } = await import("sonner");

    result.current.uploadFiles([makeFile("a.pdf"), makeFile("b.pdf")]);

    await waitFor(() => expect(mockedDocumentsApi.upload).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(result.current.isUploading).toBe(false));
    expect(toast.success).toHaveBeenCalledWith(expect.stringContaining("a.pdf"));
    expect(toast.success).toHaveBeenCalledWith(expect.stringContaining("b.pdf"));
  });

  it("reports isUploading while an upload is in flight, and false once it settles", async () => {
    let resolveUpload!: (doc: DocChatDocument) => void;
    mockedDocumentsApi.upload.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveUpload = resolve;
        })
    );

    const { result } = renderHookWithClient(() => useMultiFileUpload());

    expect(result.current.isUploading).toBe(false);
    result.current.uploadFiles([makeFile("a.pdf")]);

    await waitFor(() => expect(result.current.isUploading).toBe(true));

    resolveUpload(makeDocument());
    await waitFor(() => expect(result.current.isUploading).toBe(false));
  });

  it("reports a per-file error without blocking the other uploads", async () => {
    mockedDocumentsApi.upload.mockImplementation((file: File) =>
      file.name === "bad.pdf"
        ? Promise.reject(new Error("Corrupted file."))
        : Promise.resolve(makeDocument({ id: file.name, original_filename: file.name }))
    );

    const { result } = renderHookWithClient(() => useMultiFileUpload());
    const { toast } = await import("sonner");

    result.current.uploadFiles([makeFile("bad.pdf"), makeFile("good.pdf")]);

    await waitFor(() => expect(mockedDocumentsApi.upload).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(result.current.isUploading).toBe(false));
    expect(toast.error).toHaveBeenCalledWith(expect.stringContaining("bad.pdf"));
    expect(toast.success).toHaveBeenCalledWith(expect.stringContaining("good.pdf"));
  });
});
