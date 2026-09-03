import { FileStack, FileText, MessagesSquare, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/common/EmptyState";
import { NewChatButton } from "@/components/chat/NewChatButton";
import { StatusBadge } from "@/components/documents/StatusBadge";
import { UploadDropzone } from "@/components/documents/UploadDropzone";
import { useConversationsQuery } from "@/hooks/useConversations";
import { useDocumentsQuery, useMultiFileUpload } from "@/hooks/useDocuments";
import { formatRelativeTime } from "@/lib/utils";

export function Dashboard() {
  const { data: documentsData } = useDocumentsQuery();
  const { data: conversationsData } = useConversationsQuery();
  const { uploadFiles, isUploading } = useMultiFileUpload();

  const documents = documentsData?.documents ?? [];
  const conversations = conversationsData?.conversations ?? [];
  const pagesIndexed = documents.reduce((sum, doc) => sum + (doc.page_count ?? 0), 0);

  return (
    <div className="mx-auto max-w-5xl space-y-10 p-6 sm:p-8">
      <div>
        <h1 className="text-[28px] font-semibold tracking-tight">Welcome to DocChat</h1>
        <p className="mt-1.5 text-[15px] text-muted-foreground">
          Chat with your documents. Get answers grounded in your sources.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard icon={FileStack} label="Documents" value={documents.length} />
        <StatCard icon={MessagesSquare} label="Conversations" value={conversations.length} />
        <StatCard icon={FileText} label="Pages Indexed" value={pagesIndexed} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section className="space-y-3.5">
          <div className="flex h-8 items-center justify-between">
            <h2 className="text-[15px] font-semibold tracking-tight">Recent Documents</h2>
            {documents.length > 5 && (
              <span className="text-xs text-muted-foreground">
                +{documents.length - 5} more in sidebar
              </span>
            )}
          </div>

          {documents.length === 0 ? (
            <UploadDropzone onUpload={uploadFiles} isUploading={isUploading} />
          ) : (
            <Card className="overflow-hidden">
              <CardContent className="divide-y divide-border p-0">
                {documents.slice(0, 5).map((document) => (
                  <Link
                    key={document.id}
                    to={`/documents/${document.id}`}
                    className="flex items-center justify-between gap-3 px-4 py-3 text-sm transition-colors hover:bg-accent"
                  >
                    <span className="min-w-0 flex-1 truncate">{document.original_filename}</span>
                    <StatusBadge status={document.status} />
                  </Link>
                ))}
              </CardContent>
            </Card>
          )}
        </section>

        <section className="space-y-3.5">
          <div className="flex h-8 items-center justify-between">
            <h2 className="text-[15px] font-semibold tracking-tight">Recent Conversations</h2>
            <NewChatButton variant="secondary" size="sm" />
          </div>

          {conversations.length === 0 ? (
            <EmptyState
              icon={Sparkles}
              title="No conversations yet"
              description="Choose a document and start asking questions."
            />
          ) : (
            <Card className="overflow-hidden">
              <CardContent className="divide-y divide-border p-0">
                {conversations.slice(0, 5).map((conversation) => (
                  <Link
                    key={conversation.id}
                    to={`/chat/${conversation.id}`}
                    className="flex items-center justify-between gap-3 px-4 py-3 text-sm transition-colors hover:bg-accent"
                  >
                    <span className="min-w-0 flex-1 truncate">{conversation.title}</span>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {formatRelativeTime(conversation.updated_at)}
                    </span>
                  </Link>
                ))}
              </CardContent>
            </Card>
          )}
        </section>
      </div>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof FileStack;
  label: string;
  value: number;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3.5 p-5">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10">
          <Icon className="h-[18px] w-[18px] text-primary" aria-hidden="true" />
        </div>
        <div>
          <p className="text-2xl font-semibold leading-none tracking-tight">{value}</p>
          <p className="mt-1 text-xs text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}
