"use client";

import { Check, X } from "lucide-react";
import { useState } from "react";

import { ExamShell } from "@/components/exam/exam-shell";
import { SkillsPanel } from "@/components/progress/skills-panel";
import { Button } from "@/components/ui/button";
import { Card, Eyebrow, SectionTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/states";
import { WritingExam } from "@/components/writing/writing-exam";
import { WritingFeedback } from "@/components/writing/writing-feedback";
import type { Schemas } from "@/lib/api/client";
import { fr } from "@/lib/french";
import {
  useStartDrill,
  useStartWritingDrill,
  useSubmitDrill,
  useSubmitWritingDrill,
} from "@/lib/queries";

type Choice = "CO" | "CE" | "EE";

const DRILLS: { skill: Choice; title: string; detail: string }[] = [
  {
    skill: "CO",
    title: "Compréhension orale",
    detail: "10 questions · about 9 minutes · each recording plays once",
  },
  { skill: "CE", title: "Compréhension écrite", detail: "10 questions · about 15 minutes" },
  {
    skill: "EE",
    title: "Expression écrite",
    detail: "One task matched to your level · 10–30 minutes · graded on /20",
  },
];

export function DrillsPage() {
  const [choice, setChoice] = useState<Choice | null>(null);

  return (
    <div className="space-y-6">
      <header>
        <Eyebrow>Exam conditions · counts at half weight</Eyebrow>
        <h1 className="mt-1 font-serif text-3xl font-semibold">Timed drills</h1>
      </header>

      {choice === null && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            {DRILLS.map((d) => (
              <Card key={d.skill} className="flex flex-col justify-between gap-4">
                <div>
                  <SectionTitle lang="fr">{d.title}</SectionTitle>
                  <p className="mt-1 text-sm text-muted">{d.detail}</p>
                </div>
                <Button onClick={() => setChoice(d.skill)}>Start</Button>
              </Card>
            ))}
          </div>
          <p className="text-sm text-muted">
            Unseen tasks, no hints, no going back. The server sets the deadline; time running out
            submits your answers.
          </p>
          <SkillsPanel />
        </>
      )}
      {(choice === "CO" || choice === "CE") && (
        <McqDrill skill={choice} onDone={() => setChoice(null)} />
      )}
      {choice === "EE" && <WritingDrill onDone={() => setChoice(null)} />}
    </div>
  );
}

function McqDrill({ skill, onDone }: { skill: "CO" | "CE"; onDone: () => void }) {
  const start = useStartDrill();
  const submit = useSubmitDrill();
  const drill = start.data;
  const outcome = submit.data;

  if (start.isError) return <ErrorState error={start.error} />;
  if (submit.isError) return <ErrorState error={submit.error} />;
  if (!drill) {
    return (
      <Begin
        onBegin={() => start.mutate({ skill, count: 10 })}
        pending={start.isPending}
        onCancel={onDone}
      />
    );
  }
  if (!outcome) {
    return (
      <ExamShell
        items={drill.items}
        deadline={drill.deadline}
        submitting={submit.isPending}
        onSubmit={(answers) => submit.mutate({ runId: drill.run_id, answers })}
      />
    );
  }
  return (
    <div className="space-y-4">
      <Card className="text-center">
        <p className="font-serif text-4xl font-semibold tabular-nums">
          {Math.round(outcome.score * 100)}%
        </p>
        <LevelLine level={outcome.level} scale="/699" />
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
      <Button variant="secondary" onClick={onDone}>
        Back to drills
      </Button>
    </div>
  );
}

function WritingDrill({ onDone }: { onDone: () => void }) {
  const start = useStartWritingDrill();
  const submit = useSubmitWritingDrill();
  const drill = start.data;

  if (start.isError) return <ErrorState error={start.error} />;
  if (submit.isError) return <ErrorState error={submit.error} />;
  if (!drill) {
    return <Begin onBegin={() => start.mutate()} pending={start.isPending} onCancel={onDone} />;
  }
  if (!submit.data) {
    return (
      <WritingExam
        drill={drill}
        submitting={submit.isPending}
        onSubmit={(text) => submit.mutate({ runId: drill.run_id, text })}
      />
    );
  }
  return (
    <div className="space-y-4">
      {submit.data.level && (
        <Card className="text-center">
          <LevelLine level={submit.data.level} scale="/20" />
        </Card>
      )}
      <WritingFeedback result={submit.data} />
      <Button variant="secondary" onClick={onDone}>
        Back to drills
      </Button>
    </div>
  );
}

function Begin({
  onBegin,
  onCancel,
  pending,
}: {
  onBegin: () => void;
  onCancel: () => void;
  pending: boolean;
}) {
  return (
    <Card className="space-y-4">
      <p>The clock starts when you press Begin and can&apos;t be paused.</p>
      <div className="flex gap-3">
        <Button onClick={onBegin} disabled={pending}>
          Begin
        </Button>
        <Button variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </Card>
  );
}

function LevelLine({
  level,
  scale,
}: {
  level: Schemas["SkillLevelOut"] | null | undefined;
  scale: string;
}) {
  if (!level) return null;
  return (
    <p className="mt-1 text-muted">
      Estimated {Math.round(level.score)}
      {scale} · {level.cefr} · NCLC {level.nclc ?? "below 4"}
    </p>
  );
}
