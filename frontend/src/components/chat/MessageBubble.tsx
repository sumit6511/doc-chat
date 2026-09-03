import { useState } from "react";
import { Check, Copy, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Button } from "@/components/ui/button";
import { SourceCard } from "@/components/chat/SourceCard";
import { cn } from "@/lib/utils";
import type { Message } from "@/types";

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  if (isUser) {
    return (
      <div className="flex animate-slide-up flex-col items-end gap-1.5">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-sm leading-relaxed text-primary-foreground sm:max-w-[70%]">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="group flex animate-slide-up gap-3">
      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10">
        <Sparkles className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
      </div>

      <div className="min-w-0 flex-1 space-y-2.5">
        <div className="prose prose-sm max-w-none text-sm leading-relaxed text-foreground dark:prose-invert prose-p:my-2 prose-pre:my-2 prose-headings:mt-4 prose-headings:mb-2 first:prose-p:mt-0 last:prose-p:mb-0">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        </div>

        <div className="flex items-center gap-1 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-6 w-6 text-muted-foreground"
            onClick={handleCopy}
            aria-label={copied ? "Copied" : "Copy answer"}
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          </Button>
        </div>

        {message.sources.length > 0 && (
          <div className="space-y-1.5 pt-1">
            <p className="text-xs font-medium text-muted-foreground">Sources</p>
            <div className="grid gap-1.5 sm:grid-cols-2">
              {message.sources.map((source) => (
                <SourceCard key={source.chunk_id} source={source} />
              ))}
            </div>
          </div>
        )}

        {message.debug_retrieved_chunks && message.debug_retrieved_chunks.length > 0 && (
          <details className="rounded-lg border border-dashed border-border px-3 py-2 text-xs">
            <summary className="cursor-pointer select-none font-medium text-muted-foreground">
              Retrieved chunks (debug)
            </summary>
            <ol className="mt-2 space-y-1">
              {message.debug_retrieved_chunks.map((chunk, index) => (
                <li
                  key={`${chunk.filename}-${chunk.page_number}-${index}`}
                  className={cn("flex justify-between gap-2", !chunk.used && "opacity-50")}
                >
                  <span className="truncate">
                    {index + 1}. {chunk.filename} · p.{chunk.page_number}
                  </span>
                  <span className="shrink-0 font-mono">{chunk.score.toFixed(2)}</span>
                </li>
              ))}
            </ol>
          </details>
        )}
      </div>
    </div>
  );
}
