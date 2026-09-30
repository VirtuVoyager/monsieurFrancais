"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen } from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Loading } from "@/components/ui/states";
import { api, unwrap } from "@/lib/api/client";

export const authKey = ["auth"] as const;

export function AuthGate({ children }: { children: ReactNode }) {
  const status = useQuery({ queryKey: authKey, queryFn: () => unwrap(api.GET("/auth/status")) });
  if (status.isPending) return <Loading />;
  if (status.data?.authenticated) return children;
  return <PassphraseForm firstTime={!status.data?.configured} />;
}

function PassphraseForm({ firstTime }: { firstTime: boolean }) {
  const queryClient = useQueryClient();
  const [passphrase, setPassphrase] = useState("");
  const submit = useMutation({
    mutationFn: () =>
      unwrap(api.POST(firstTime ? "/auth/setup" : "/auth/login", { body: { passphrase } })),
    onSuccess: () => queryClient.invalidateQueries(),
  });

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    submit.mutate();
  };

  return (
    <div className="grid min-h-dvh place-items-center px-4">
      <Card className="w-full max-w-sm">
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="flex items-center gap-2">
            <BookOpen className="size-6 text-accent" aria-hidden />
            <h1 className="font-serif text-xl font-semibold">Monsieur Français</h1>
          </div>
          <p className="text-sm text-muted">
            {firstTime
              ? "Choose a passphrase (8+ characters). It protects your recordings and progress."
              : "Enter your passphrase."}
          </p>
          <label className="block text-sm font-medium">
            Passphrase
            <input
              type="password"
              autoComplete={firstTime ? "new-password" : "current-password"}
              autoFocus
              value={passphrase}
              onChange={(e) => setPassphrase(e.target.value)}
              className="mt-1 w-full rounded-xl border border-line bg-surface px-3 py-2 outline-none focus:border-accent"
            />
          </label>
          {submit.isError && (
            <p role="alert" className="text-sm text-danger">
              {submit.error.message}
            </p>
          )}
          <Button type="submit" className="w-full" disabled={!passphrase || submit.isPending}>
            {firstTime ? "Set passphrase" : "Sign in"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
