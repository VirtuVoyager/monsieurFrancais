"use client";

import { ExamShell } from "@/components/exam/exam-shell";
import { Button, ButtonLink } from "@/components/ui/button";
import { Card, Eyebrow } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/states";
import { useStartPlacement, useSubmitPlacement } from "@/lib/queries";

const SKILL_NAMES: Record<string, string> = { CO: "Listening", CE: "Reading" };

export function PlacementPage() {
  const start = useStartPlacement();
  const submit = useSubmitPlacement();
  const run = start.data;
  const outcome = submit.data;

  return (
    <div className="space-y-6">
      <header>
        <Eyebrow>About 20 minutes · counts as exam evidence</Eyebrow>
        <h1 className="mt-1 font-serif text-3xl font-semibold">Placement test</h1>
      </header>
      {start.isError && <ErrorState error={start.error} />}
      {submit.isError && <ErrorState error={submit.error} />}

      {!run && (
        <Card className="space-y-4">
          <p>
            Sixteen questions from A1 to B2: listening first, then reading. It sets your starting
            skill bars and skips modules below your level. Your weaker skill decides where you
            start, as it does for IRCC.
          </p>
          <p className="text-sm text-muted">
            Writing and speaking are placed later, once graded tasks are available.
          </p>
          <Button onClick={() => start.mutate()} disabled={start.isPending}>
            Begin
          </Button>
        </Card>
      )}

      {run && !outcome && (
        <ExamShell
          items={run.items}
          deadline={run.deadline}
          submitting={submit.isPending}
          onSubmit={(answers) => submit.mutate({ runId: run.run_id, answers })}
        />
      )}

      {outcome && (
        <Card className="space-y-5">
          <div>
            <Eyebrow>You start at</Eyebrow>
            <p className="font-serif text-4xl font-semibold">{outcome.placed_level}</p>
            <p className="mt-1 text-sm text-muted">
              {outcome.modules_placed > 0
                ? `${outcome.modules_placed} earlier modules marked as placed.`
                : "Your path starts at the first module."}
            </p>
          </div>
          <dl className="grid gap-4 sm:grid-cols-2">
            {Object.entries(outcome.levels).map(([skill, level]) => (
              <div key={skill} className="rounded-xl border border-line p-4">
                <dt className="text-sm text-muted">{SKILL_NAMES[skill] ?? skill}</dt>
                <dd className="mt-1 font-medium">
                  {level
                    ? `${Math.round(level.score)}/699 · ${level.cefr} · NCLC ${level.nclc ?? "below 4"}`
                    : "Not assessed"}
                </dd>
              </div>
            ))}
          </dl>
          <ButtonLink href="/path">Open your path</ButtonLink>
        </Card>
      )}
    </div>
  );
}
