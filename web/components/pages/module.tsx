"use client";

import { ArrowLeft, Check, Circle } from "lucide-react";
import Link from "next/link";

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
    <div className="space-y-6">
      <Link
        href="/path"
        className="text-muted hover:text-ink inline-flex items-center gap-1 text-sm"
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
        <p className="text-muted mt-2 max-w-2xl" lang="fr">
          {fr(m.summary)}
        </p>
      </header>

      <Card className="p-0 sm:p-0">
        <ol className="divide-line divide-y">
          {m.lessons.map((lesson) => (
            <li key={lesson.id}>
              <Link
                href={`/lessons/${lesson.id}`}
                className="hover:bg-surface-2 flex items-center gap-4 px-5 py-4 transition-colors sm:px-6"
              >
                {lesson.done ? (
                  <Check className="text-success size-5" aria-label="Done" />
                ) : (
                  <Circle className="text-line size-5" aria-label="Not done" />
                )}
                <div className="flex-1">
                  <p className="text-muted text-xs">{KIND_LABELS[lesson.kind] ?? lesson.kind}</p>
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
          <p className="text-muted text-sm">
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
  );
}
