"use client";

import { Check, X } from "lucide-react";

import { ExamShell } from "@/components/exam/exam-shell";
import { SkillsPanel } from "@/components/progress/skills-panel";
import { Button } from "@/components/ui/button";
import { Card, Eyebrow, SectionTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/states";
import { fr } from "@/lib/french";
import { useStartDrill, useSubmitDrill } from "@/lib/queries";

const DRILLS = [
  {
    skill: "CO" as const,
    title: "Compréhension orale",
    detail: "10 questions · about 9 minutes · each recording plays once",
  },
  {
    skill: "CE" as const,
    title: "Compréhension écrite",
    detail: "10 questions · about 15 minutes",
  },
];

export function DrillsPage() {
  const start = useStartDrill();
  const submit = useSubmitDrill();
  const drill = start.data;
  const outcome = submit.data;

  const reset = () => {
    start.reset();
    submit.reset();
  };

  return (
    <div className="space-y-6">
      <header>
        <Eyebrow>Exam conditions · counts at half weight</Eyebrow>
        <h1 className="mt-1 font-serif text-3xl font-semibold">Timed drills</h1>
      </header>
      {start.isError && <ErrorState error={start.error} />}
      {submit.isError && <ErrorState error={submit.error} />}

      {!drill && (
        <div className="grid gap-4 sm:grid-cols-2">
          {DRILLS.map((d) => (
            <Card key={d.skill} className="flex flex-col justify-between gap-4">
              <div>
                <SectionTitle lang="fr">{d.title}</SectionTitle>
                <p className="mt-1 text-sm text-muted">{d.detail}</p>
                <p className="mt-3 text-sm text-muted">
                  Unseen questions, no hints, no going back. The timer is set by the server; time
                  running out submits your answers.
                </p>
              </div>
              <Button
                onClick={() => start.mutate({ skill: d.skill, count: 10 })}
                disabled={start.isPending}
              >
                Start
              </Button>
            </Card>
          ))}
        </div>
      )}

      {drill && !outcome && (
        <ExamShell
          items={drill.items}
          deadline={drill.deadline}
          submitting={submit.isPending}
          onSubmit={(answers) => submit.mutate({ runId: drill.run_id, answers })}
        />
      )}

      {outcome && (
        <div className="space-y-4">
          <Card className="text-center">
            <p className="font-serif text-4xl font-semibold tabular-nums">
              {Math.round(outcome.score * 100)}%
            </p>
            {outcome.level && (
              <p className="mt-1 text-muted">
                Estimated {Math.round(outcome.level.score)}/699 · {outcome.level.cefr} · NCLC{" "}
                {outcome.level.nclc ?? "below 4"}
              </p>
            )}
          </Card>
          <Card className="space-y-2">
            {outcome.results.map((r, i) => (
              <div key={r.item_id} className="flex items-start gap-3 text-sm" lang="fr">
                {r.correct ? (
                  <Check className="mt-0.5 size-4 text-success" aria-label="Correct" />
                ) : (
                  <X className="mt-0.5 size-4 text-danger" aria-label="Incorrect" />
                )}
                <span>
                  <span className="text-muted">{i + 1}.</span> {fr(r.expected)}
                </span>
              </div>
            ))}
          </Card>
          <Button variant="secondary" onClick={reset}>
            Another drill
          </Button>
        </div>
      )}

      {!drill && <SkillsPanel />}
    </div>
  );
}
