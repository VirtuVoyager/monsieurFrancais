import type { ReactNode } from "react";

import { Card } from "./card";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" className="animate-pulse py-16 text-center text-muted">
      {label}
    </div>
  );
}

export function ErrorState({ error }: { error: Error }) {
  return (
    <Card role="alert" className="border-danger/40 bg-danger-soft text-danger">
      {error.message}
    </Card>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <Card className="py-10 text-center">
      <p className="font-serif text-lg font-semibold">{title}</p>
      {children && <div className="mt-2 text-sm text-muted">{children}</div>}
    </Card>
  );
}
