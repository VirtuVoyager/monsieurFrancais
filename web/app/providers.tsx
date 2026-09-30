"use client";

import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { authKey } from "@/components/shell/auth-gate";
import { ApiError } from "@/lib/api/client";

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(() => {
    // An expired session anywhere sends the user back to the passphrase screen.
    const onError = (error: Error) => {
      if (error instanceof ApiError && error.status === 401) {
        void client.invalidateQueries({ queryKey: authKey });
      }
    };
    const client: QueryClient = new QueryClient({
      queryCache: new QueryCache({ onError }),
      mutationCache: new MutationCache({ onError }),
      defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
    });
    return client;
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
