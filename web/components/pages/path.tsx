"use client";

import { Check, Lock } from "lucide-react";
import Link from "next/link";

import { CoverageBar } from "@/components/progress/coverage-bar";
import { Badge } from "@/components/ui/badge";
import { Card, Eyebrow } from "@/components/ui/card";
import { cx } from "@/components/ui/cx";
import { ErrorState, Loading } from "@/components/ui/states";
import type { Schemas } from "@/lib/api/client";
import { fr } from "@/lib/french";
import { usePath } from "@/lib/queries";

export function PathPage() {
  const path = usePath();
  if (path.isPending) return <Loading />;
  if (path.isError) return <ErrorState error={path.error} />;

  return (
    <div className="space-y-8">
      <header className="space-y-4">
        <h1 className="font-serif text-3xl font-semibold">Your path</h1>
        <Card>
          <CoverageBar coverage={path.data.coverage} />
        </Card>
      </header>
      {path.data.levels.map((level) => (
        <section key={level.id} aria-labelledby={`level-${level.id}`} className="space-y-3">
          <div className="flex items-baseline justify-between">
            <h2 id={`level-${level.id}`} className="font-serif text-2xl font-semibold">
              {level.id}
            </h2>
            <span className="text-muted text-sm">
              {level.covered} / {level.total} covered
            </span>
          </div>
          <ol className="space-y-3">
            {level.modules.map((module) => (
              <li key={module.id}>
                <ModuleRow module={module} />
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}

function ModuleRow({ module }: { module: Schemas["ModuleSummary"] }) {
  const locked = module.status === "locked";
  const done = module.status === "covered" || module.status === "placed";
  const body = (
    <Card
      className={cx(
        "flex items-center gap-4 transition-colors",
        locked ? "opacity-60" : "hover:border-accent/50",
      )}
    >
      <span
        className={cx(
          "grid size-10 shrink-0 place-items-center rounded-full font-serif font-semibold",
          done ? "bg-success-soft text-success" : "bg-accent-soft text-accent",
        )}
      >
        {done ? (
          <Check className="size-5" aria-hidden />
        ) : locked ? (
          <Lock className="size-4" aria-hidden />
        ) : (
          module.order
        )}
      </span>
      <div className="min-w-0 flex-1">
        <Eyebrow>{module.theme}</Eyebrow>
        <p className="truncate font-medium" lang="fr">
          {fr(module.title)}
        </p>
      </div>
      <div className="text-right text-sm">
        <StatusBadge status={module.status} />
        <p className="text-muted mt-1 text-xs tabular-nums">
          {module.lessons_done}/{module.lessons_total} lessons
        </p>
      </div>
    </Card>
  );
  return locked ? body : <Link href={`/modules/${module.id}`}>{body}</Link>;
}

function StatusBadge({ status }: { status: Schemas["Status"] }) {
  const tone = {
    locked: "neutral",
    open: "accent",
    covered: "success",
    placed: "success",
  } as const;
  return <Badge tone={tone[status]}>{status}</Badge>;
}
