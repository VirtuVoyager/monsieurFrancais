"use client";

import { ArrowLeft, Check, Circle } from "lucide-react";
import Link from "next/link";

import { Glossed } from "@/components/glossary/glossed";

import { ButtonLink } from "@/components/ui/button";
import { Card, Eyebrow } from "@/components/ui/card";
import { ErrorState, Loading } from "@/components/ui/states";
import { fr } from "@/lib/french";
import { useModule } from "@/lib/queries";

const KIND_LABELS: Record<string, string> = {
  grammar: "Grammar",
  vocab: "Vocabulary",
  sentences: "Model sentences",
  listening: "Listening",
  reading: "Reading",
  writing: "Writing",
  speaking: "Speaking",
};

export function ModulePage({ id }: { id: string }) {
  const moduleQuery = useModule(id);
  if (moduleQuery.isPending) return <Loading />;
  if (moduleQuery.isError) return <ErrorState error={moduleQuery.error} />;
  const m = moduleQuery.data;

  return (
    <Glossed moduleId={id}>
      <div className="space-y-6">
        <Link
          href="/path"
          className="inline-flex items-center gap-1 text-sm text-muted hover:text-ink"
        >
          <ArrowLeft className="size-4" aria-hidden /> Path
        </Link>
        <header>
          <Eyebrow>
            {m.level} · Module {m.order} · {m.theme}
          </Eyebrow>
          <h1 className="mt-1 font-serif text-3xl font-semibold" lang="fr">
            {fr(m.title)}
          </h1>
          <p className="mt-2 max-w-2xl text-muted" lang="fr">
            {fr(m.summary)}
          </p>
        </header>

        <Card className="p-0 sm:p-0">
          <ol className="divide-y divide-line">
            {m.lessons.map((lesson) => (
              <li key={lesson.id}>
                <Link
                  href={`/lessons/${lesson.id}`}
                  className="flex items-center gap-4 px-5 py-4 transition-colors hover:bg-surface-2 sm:px-6"
                >
                  {lesson.done ? (
                    <Check className="size-5 text-success" aria-label="Done" />
                  ) : (
                    <Circle className="size-5 text-line" aria-label="Not done" />
                  )}
                  <div className="flex-1">
                    <p className="text-xs text-muted">{KIND_LABELS[lesson.kind] ?? lesson.kind}</p>
                    <p className="font-medium" lang="fr">
                      {fr(lesson.title)}
                    </p>
                  </div>
                </Link>
              </li>
            ))}
          </ol>
        </Card>

        <Card className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-medium">Module check</p>
            <p className="text-sm text-muted">
              {m.check_score !== null
                ? `Best score ${Math.round(m.check_score * 100)}% · 80% covers the module`
                : "Score 80% or more to cover this module."}
            </p>
          </div>
          <ButtonLink
            href={`/modules/${m.id}/check`}
            aria-disabled={!m.can_take_check}
            className={m.can_take_check ? "" : "pointer-events-none opacity-50"}
          >
            {m.can_take_check ? "Take the check" : "Finish all lessons first"}
          </ButtonLink>
        </Card>
      </div>
    </Glossed>
  );
}
