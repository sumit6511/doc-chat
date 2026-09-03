import { lazy } from "react";
import { createBrowserRouter } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";

// Route-level code splitting: each page (and whatever it alone depends on —
// e.g. Chat pulls in react-markdown/remark-gfm for rendering answers, which
// Dashboard and Document never need) becomes its own chunk instead of all
// three shipping in the single initial bundle. Pages use named exports, so
// each dynamic import is adapted into the { default } shape lazy() expects.
const Dashboard = lazy(() =>
  import("@/pages/Dashboard").then((module) => ({ default: module.Dashboard }))
);
const Chat = lazy(() => import("@/pages/Chat").then((module) => ({ default: module.Chat })));
const Document = lazy(() =>
  import("@/pages/Document").then((module) => ({ default: module.Document }))
);

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
