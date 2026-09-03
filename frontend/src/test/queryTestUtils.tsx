import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, type RenderHookOptions } from "@testing-library/react";

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

/**
 * renderHook wrapped in a fresh QueryClientProvider — pass an existing
 * `queryClient` (e.g. to spy on `invalidateQueries` before the hook runs)
 * or let one be created automatically.
 */
export function renderHookWithClient<TResult, TProps>(
  hook: (props: TProps) => TResult,
  options?: RenderHookOptions<TProps> & { queryClient?: QueryClient }
) {
  const queryClient = options?.queryClient ?? createTestQueryClient();
  function wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }

  return { ...renderHook(hook, { ...options, wrapper }), queryClient };
}
