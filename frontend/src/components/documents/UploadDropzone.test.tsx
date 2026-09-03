import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { UploadDropzone } from "@/components/documents/UploadDropzone";

function makeFile(name: string, sizeBytes: number, type = "application/pdf") {
  const file = new File(["%PDF-1.4 fake content"], name, { type });
  Object.defineProperty(file, "size", { value: sizeBytes });
  return file;
}

describe("UploadDropzone", () => {
  it("calls onUpload for a valid PDF selected via the file input", () => {
    let uploadedFile: File | undefined;
    const onUpload = vi.fn((file: File) => {
      uploadedFile = file;
    });
    render(<UploadDropzone onUpload={onUpload} />);

    const input = screen.getByLabelText(/upload a pdf document/i);
    fireEvent.change(input, { target: { files: [makeFile("notes.pdf", 1024)] } });

    expect(onUpload).toHaveBeenCalledTimes(1);
    expect(uploadedFile?.name).toBe("notes.pdf");
  });

  it("rejects a non-PDF file and does not call onUpload", () => {
    const onUpload = vi.fn();
    render(<UploadDropzone onUpload={onUpload} />);

    const input = screen.getByLabelText(/upload a pdf document/i);
    fireEvent.change(input, { target: { files: [makeFile("notes.txt", 1024, "text/plain")] } });

    expect(onUpload).not.toHaveBeenCalled();
  });

  it("rejects a file over the size limit and does not call onUpload", () => {
    const onUpload = vi.fn();
    render(<UploadDropzone onUpload={onUpload} />);

    const input = screen.getByLabelText(/upload a pdf document/i);
    const oversized = makeFile("big.pdf", 21 * 1024 * 1024);
    fireEvent.change(input, { target: { files: [oversized] } });

    expect(onUpload).not.toHaveBeenCalled();
  });

  it("disables the choose-file button while uploading", () => {
    render(<UploadDropzone onUpload={vi.fn()} isUploading />);
    expect(screen.getByRole("button", { name: /uploading/i })).toBeDisabled();
  });
});
