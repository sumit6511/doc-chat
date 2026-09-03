import { useCallback, useId, useRef, useState } from "react";
import { FileUp, UploadCloud } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const MAX_FILE_SIZE_MB = 20;

interface UploadDropzoneProps {
  onUpload: (files: File[]) => void;
  isUploading?: boolean;
}

export function UploadDropzone({ onUpload, isUploading }: UploadDropzoneProps) {
  const [isDragActive, setIsDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const inputId = useId();

  const validateAndUpload = useCallback(
    (fileList: FileList | null) => {
      if (!fileList || fileList.length === 0) return;

      const validFiles: File[] = [];
      for (const file of Array.from(fileList)) {
        if (!file.name.toLowerCase().endsWith(".pdf")) {
          toast.error(`${file.name}: only PDF files are supported.`);
          continue;
        }
        if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
          toast.error(`${file.name}: exceeds the ${MAX_FILE_SIZE_MB} MB upload limit.`);
          continue;
        }
        validFiles.push(file);
      }

      if (validFiles.length > 0) onUpload(validFiles);
    },
    [onUpload]
  );

  return (
    <div
      className={cn(
        "flex flex-col items-center gap-3 rounded-xl border-2 border-dashed px-4 py-8 text-center transition-colors",
        isDragActive ? "border-primary bg-primary/5" : "border-border hover:border-muted-foreground/30"
      )}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragActive(true);
      }}
      onDragLeave={() => setIsDragActive(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragActive(false);
        validateAndUpload(e.dataTransfer.files);
      }}
    >
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
        <UploadCloud className="h-5 w-5 text-primary" aria-hidden="true" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium">Drag & drop PDFs here</p>
        <p className="text-xs text-muted-foreground">or choose files below</p>
      </div>

      <label htmlFor={inputId} className="sr-only">
        Upload PDF documents
      </label>
      <input
        id={inputId}
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        multiple
        className="sr-only"
        disabled={isUploading}
        onChange={(e) => {
          validateAndUpload(e.target.files);
          e.target.value = "";
        }}
      />
      <Button
        type="button"
        size="sm"
        variant="secondary"
        disabled={isUploading}
        onClick={() => inputRef.current?.click()}
      >
        <FileUp className="h-3.5 w-3.5" />
        {isUploading ? "Uploading…" : "Choose Files"}
      </Button>

      <p className="text-xs text-muted-foreground">PDF · Max {MAX_FILE_SIZE_MB} MB each</p>
    </div>
  );
}
