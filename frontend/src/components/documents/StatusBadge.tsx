import { CheckCircle2, CircleAlert, Loader2, UploadCloud } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { DocumentStatus } from "@/types";

const STATUS_CONFIG: Record<
  DocumentStatus,
  { label: string; icon: typeof CheckCircle2; variant: "default" | "success" | "destructive" | "secondary" }
> = {
  UPLOADING: { label: "Uploading", icon: UploadCloud, variant: "secondary" },
  PROCESSING: { label: "Processing", icon: Loader2, variant: "default" },
  READY: { label: "Ready", icon: CheckCircle2, variant: "success" },
  FAILED: { label: "Failed", icon: CircleAlert, variant: "destructive" },
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;
  return (
    <Badge variant={config.variant}>
      <Icon className={`h-3 w-3 ${status === "PROCESSING" ? "animate-spin" : ""}`} aria-hidden="true" />
      {config.label}
    </Badge>
  );
}
