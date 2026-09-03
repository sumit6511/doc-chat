import { useState } from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { Outlet } from "react-router-dom";

import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";

export function AppShell() {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  return (
    <div className="flex h-dvh flex-col">
      <Topbar onOpenSidebar={() => setMobileSidebarOpen(true)} />

      <div className="flex min-h-0 flex-1">
        <aside className="hidden w-72 shrink-0 border-r border-border lg:block">
          <Sidebar />
        </aside>

        <DialogPrimitive.Root open={mobileSidebarOpen} onOpenChange={setMobileSidebarOpen}>
          <DialogPrimitive.Portal>
            <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/50 lg:hidden" />
            <DialogPrimitive.Content
              className="fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] border-r border-border bg-background shadow-lg lg:hidden"
              aria-describedby={undefined}
            >
              <DialogPrimitive.Title className="sr-only">Documents and conversations</DialogPrimitive.Title>
              <div className="flex h-14 items-center justify-end border-b border-border px-2">
                <DialogPrimitive.Close
                  className="rounded-sm p-2 opacity-70 hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  aria-label="Close sidebar"
                >
                  <X className="h-4 w-4" />
                </DialogPrimitive.Close>
              </div>
              <div className="h-[calc(100%-3.5rem)]">
                <Sidebar />
              </div>
            </DialogPrimitive.Content>
          </DialogPrimitive.Portal>
        </DialogPrimitive.Root>

        <main className="min-w-0 flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
