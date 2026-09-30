"use client";

import { ArrowLeft, Check, X } from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";

import { Exercise, type ExerciseResponse } from "@/components/exercise/exercise";
import { Button, ButtonLink } from "@/components/ui/button";
import { Card, Eyebrow } from "@/components/ui/card";
import { cx } from "@/components/ui/cx";
import { ErrorState } from "@/components/ui/states";
import { fr } from "@/lib/french";
import { useModule, useStartCheck, useSubmitCheck } from "@/lib/queries";

export function ModuleCheckPage({ moduleId }: { moduleId: string }) {
  const moduleQuery = useModule(moduleId);
  const start = useStartCheck(moduleId);
  const submit = useSubmitCheck(moduleId);
  const answers = useRef(new Map<string, ExerciseResponse>());
  const [answeredCount, setAnsweredCount] = useState(0);

  const run = start.data;
  const outcome = submit.data;

  const record = (itemId: string, response: ExerciseResponse) => {
    answers.current.set(itemId, response);
    setAnsweredCount(answers.current.size);
  };

  const finish = () => {
    if (!run) return;
    submit.mutate({
      runId: run.run_id,
      answers: [...answers.current].map(([item_id, response]) => ({ item_id, response })),
    });
  };

  return (
    <div className="space-y-6">
      <Link
        href={`/modules/${moduleId}`}
        className="inline-flex items-center gap-1 text-sm text-muted hover:text-ink"
      >
        <ArrowLeft className="size-4" aria-hidden /> Module
      </Link>
      <header>
        <Eyebrow>Module check</Eyebrow>
        <h1 className="mt-1 font-serif text-3xl font-semibold" lang="fr">
          {moduleQuery.data ? fr(moduleQuery.data.title) : "…"}
        </h1>
      </header>

      {start.isError && <ErrorState error={start.error} />}
      {submit.isError && <ErrorState error={submit.error} />}

      {!run && (
        <Card className="space-y-3">
          <p>One attempt, no hints, answers revealed at the end. 80% or more covers the module.</p>
          <Button onClick={() => start.mutate()} disabled={start.isPending}>
            Start the check
          </Button>
        </Card>
      )}

      {run && !outcome && (
        <div className="space-y-4">
          {run.items.map((item, index) => (
            <Exercise
              key={item.id}
              number={index + 1}
              exercise={item.exercise}
              onChange={(response) => record(item.id, response)}
            />
          ))}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted tabular-nums">
              {answeredCount} / {run.items.length} answered
            </span>
            <Button onClick={finish} disabled={submit.isPending}>
              Submit
            </Button>
          </div>
        </div>
      )}

      {outcome && (
        <div className="space-y-4">
          <Card
            className={cx(
              "text-center",
              outcome.passed ? "bg-success-soft text-success" : "bg-danger-soft text-danger",
            )}
          >
            <p className="font-serif text-4xl font-semibold tabular-nums">
              {Math.round(outcome.score * 100)}%
            </p>
            <p className="mt-1 font-medium">
              {outcome.passed ? "Module covered" : "Not yet — review and try again"}
            </p>
          </Card>
          <Card className="space-y-2">
            {outcome.results.map((result, index) => (
              <div key={result.item_id} className="flex items-start gap-3 py-1" lang="fr">
                {result.correct ? (
                  <Check className="mt-0.5 size-4 text-success" aria-label="Correct" />
                ) : (
                  <X className="mt-0.5 size-4 text-danger" aria-label="Incorrect" />
                )}
                <div className="text-sm">
                  <span className="text-muted">{index + 1}.</span> {fr(result.expected)}
                  {result.explanation && <p className="text-muted">{fr(result.explanation)}</p>}
                </div>
              </div>
            ))}
          </Card>
          <ButtonLink href={outcome.passed ? "/path" : `/modules/${moduleId}`} variant="secondary">
            {outcome.passed ? "Back to the path" : "Back to the module"}
          </ButtonLink>
        </div>
      )}
    </div>
  );
}
