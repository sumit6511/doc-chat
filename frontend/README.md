# DocChat — Frontend

React + Vite + TypeScript client: document library, upload, conversations, and the chat UI with
inline citations.

See the [root README](../README.md) for architecture and how the RAG pipeline it talks to
works. This file covers just the frontend-local quick start.

## Quick start

```bash
npm install
cp .env.example .env      # VITE_API_BASE_URL defaults to http://localhost:8000/api
npm run dev
```

App: `http://localhost:5173` (requires the backend running — see `../backend/README.md`)

## Scripts

```bash
npm run dev         # Vite dev server
npm run build        # tsc -b + production build
npm run typecheck    # TypeScript strict mode, no emit
npm test             # Vitest + Testing Library
```

## Layout

```text
src/
├── app/router.tsx                     # route table
├── pages/{Dashboard,Chat,Document}.tsx
├── components/
│   ├── layout/      # AppShell (desktop split view + mobile drawer), Sidebar, Topbar
│   ├── documents/   # upload, document list, status badges
│   ├── chat/        # message list, source citations, conversation list, document scoping
│   ├── ui/          # shadcn/ui-style primitives (Radix + class-variance-authority)
│   └── common/       # EmptyState, Spinner, ConfirmDialog
├── api/             # typed fetch wrappers per resource
├── hooks/           # TanStack Query hooks (polling, mutations, cache invalidation)
└── types/           # API response types, mirrors the backend's Pydantic schemas
```
