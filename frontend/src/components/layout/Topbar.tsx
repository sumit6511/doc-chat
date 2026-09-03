import { Menu, MessageSquareText, Moon, Sun } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { useTheme } from "@/hooks/useTheme";

export function Topbar({ onOpenSidebar }: { onOpenSidebar: () => void }) {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-background px-4">
      <div className="flex items-center gap-1">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="lg:hidden"
          onClick={onOpenSidebar}
          aria-label="Open sidebar"
        >
          <Menu className="h-5 w-5" />
        </Button>
        <Link
          to="/"
          className="flex items-center gap-2 rounded-md px-1.5 py-1 text-[15px] font-semibold tracking-tight transition-opacity hover:opacity-80"
        >
          <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <MessageSquareText className="h-3.5 w-3.5" />
          </span>
          DocChat
        </Link>
      </div>

      <Button
        type="button"
        variant="ghost"
        size="icon"
        onClick={toggleTheme}
        aria-label={theme === "light" ? "Switch to dark theme" : "Switch to light theme"}
      >
        {theme === "light" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
      </Button>
    </header>
  );
}
