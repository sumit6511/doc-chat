import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { DocumentListItem } from "@/components/documents/DocumentListItem";
import { useDocumentsQuery } from "@/hooks/useDocuments";

interface DocumentScopeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialSelectedIds: string[];
  onSave: (ids: string[]) => void;
  isSaving?: boolean;
}

export function DocumentScopeDialog({
  open,
  onOpenChange,
  initialSelectedIds,
  onSave,
  isSaving,
}: DocumentScopeDialogProps) {
  const { data } = useDocumentsQuery();
  const [selected, setSelected] = useState<string[]>(initialSelectedIds);

  useEffect(() => {
    if (open) setSelected(initialSelectedIds);
  }, [open, initialSelectedIds]);

  const documents = data?.documents ?? [];

  function toggle(id: string) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((existing) => existing !== id) : [...prev, id]));
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Choose documents</DialogTitle>
          <DialogDescription>
            Leave nothing selected to search across all of your documents.
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-80 space-y-0.5 overflow-y-auto scrollbar-thin">
          {documents.length === 0 ? (
            <p className="py-4 text-sm text-muted-foreground">No documents uploaded yet.</p>
          ) : (
            documents.map((document) => (
              <DocumentListItem
                key={document.id}
                document={document}
                selectable
                selected={selected.includes(document.id)}
                onToggleSelect={toggle}
              />
            ))
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="button" onClick={() => onSave(selected)} disabled={isSaving}>
            {isSaving ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
