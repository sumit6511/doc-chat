import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { UploadDropzone } from "@/components/documents/UploadDropzone";

function makeFile(name: string, sizeBytes: number, type = "application/pdf") {
  const file = new File(["%PDF-1.4 fake content"], name, { type });
  Object.defineProperty(file, "size", { value: sizeBytes });
  return file;
}

describe("UploadDropzone", () => {
  it("calls onUpload with a valid PDF selected via the file input", () => {
    let uploadedFiles: File[] = [];
    const onUpload = vi.fn((files: File[]) => {
      uploadedFiles = files;
    });
    render(<UploadDropzone onUpload={onUpload} />);

    const input = screen.getByLabelText(/upload pdf documents/i);
    fireEvent.change(input, { target: { files: [makeFile("notes.pdf", 1024)] } });

    expect(onUpload).toHaveBeenCalledTimes(1);
    expect(uploadedFiles.map((f) => f.name)).toEqual(["notes.pdf"]);
  });

  it("calls onUpload once with all valid files when multiple are selected", () => {
    let uploadedFiles: File[] = [];
    const onUpload = vi.fn((files: File[]) => {
      uploadedFiles = files;
    });
    render(<UploadDropzone onUpload={onUpload} />);

    const input = screen.getByLabelText(/upload pdf documents/i);
    fireEvent.change(input, {
      target: { files: [makeFile("a.pdf", 1024), makeFile("b.pdf", 2048), makeFile("c.pdf", 4096)] },
    });

    expect(onUpload).toHaveBeenCalledTimes(1);
    expect(uploadedFiles.map((f) => f.name)).toEqual(["a.pdf", "b.pdf", "c.pdf"]);
  });

  it("uploads only the valid files from a mixed selection, skipping invalid ones", () => {
    let uploadedFiles: File[] = [];
    const onUpload = vi.fn((files: File[]) => {
      uploadedFiles = files;
    });
    render(<UploadDropzone onUpload={onUpload} />);

    const input = screen.getByLabelText(/upload pdf documents/i);
    fireEvent.change(input, {
      target: {
        files: [
          makeFile("good.pdf", 1024),
          makeFile("wrong-type.txt", 1024, "text/plain"),
          makeFile("too-big.pdf", 21 * 1024 * 1024),
        ],
      },
    });

    expect(onUpload).toHaveBeenCalledTimes(1);
    expect(uploadedFiles.map((f) => f.name)).toEqual(["good.pdf"]);
  });

  it("does not call onUpload when every selected file is invalid", () => {
    const onUpload = vi.fn();
    render(<UploadDropzone onUpload={onUpload} />);

    const input = screen.getByLabelText(/upload pdf documents/i);
    fireEvent.change(input, {
      target: { files: [makeFile("notes.txt", 1024, "text/plain"), makeFile("big.pdf", 21 * 1024 * 1024)] },
    });

    expect(onUpload).not.toHaveBeenCalled();
  });

  it("rejects a non-PDF file and does not call onUpload", () => {
    const onUpload = vi.fn();
    render(<UploadDropzone onUpload={onUpload} />);

    const input = screen.getByLabelText(/upload pdf documents/i);
    fireEvent.change(input, { target: { files: [makeFile("notes.txt", 1024, "text/plain")] } });

    expect(onUpload).not.toHaveBeenCalled();
  });

  it("rejects a file over the size limit and does not call onUpload", () => {
    const onUpload = vi.fn();
    render(<UploadDropzone onUpload={onUpload} />);

    const input = screen.getByLabelText(/upload pdf documents/i);
    const oversized = makeFile("big.pdf", 21 * 1024 * 1024);
    fireEvent.change(input, { target: { files: [oversized] } });

    expect(onUpload).not.toHaveBeenCalled();
  });

  it("accepts multiple file selection at once (input has the multiple attribute)", () => {
    render(<UploadDropzone onUpload={vi.fn()} />);
    const input = screen.getByLabelText(/upload pdf documents/i);
    expect(input).toHaveAttribute("multiple");
  });

  it("disables the choose-files button while uploading", () => {
    render(<UploadDropzone onUpload={vi.fn()} isUploading />);
    expect(screen.getByRole("button", { name: /uploading/i })).toBeDisabled();
  });
});
