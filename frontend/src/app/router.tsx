import { createBrowserRouter } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { Chat } from "@/pages/Chat";
import { Dashboard } from "@/pages/Dashboard";
import { Document } from "@/pages/Document";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "chat/:conversationId", element: <Chat /> },
      { path: "documents/:documentId", element: <Document /> },
    ],
  },
]);
