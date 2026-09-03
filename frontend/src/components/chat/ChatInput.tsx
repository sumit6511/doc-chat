import { useRef, type KeyboardEvent } from "react";
import { SendHorizonal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({ value, onChange, onSubmit, disabled, placeholder }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (value.trim() && !disabled) onSubmit();
    }
  }

  return (
    <div className="border-t border-border bg-background px-4 py-4 sm:px-6">
      <form
        className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-input bg-card p-1.5 pl-4 shadow-sm transition-shadow focus-within:border-ring focus-within:ring-2 focus-within:ring-ring/20"
        onSubmit={(e) => {
          e.preventDefault();
          if (value.trim() && !disabled) onSubmit();
        }}
      >
        <Textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder ?? "Ask about your documents…"}
          rows={1}
          disabled={disabled}
          aria-label="Ask a question about your documents"
          className="min-h-9 max-h-40 flex-1 resize-none border-0 bg-transparent px-0 py-2 leading-5 shadow-none focus-visible:ring-0 focus-visible:ring-offset-0"
        />
        <Button
          type="submit"
          size="icon"
          className="shrink-0 rounded-xl"
          disabled={disabled || !value.trim()}
          aria-label="Send message"
        >
          <SendHorizonal className="h-4 w-4" />
        </Button>
      </form>
      <p className="mx-auto mt-2 max-w-3xl text-center text-xs text-muted-foreground">
        DocChat can be wrong. Check the sources before relying on an answer.
      </p>
    </div>
  );
}
