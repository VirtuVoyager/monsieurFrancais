import { ArrowRight, Clock } from "lucide-react";

import type { Schemas } from "@/lib/api/client";
import { fr } from "@/lib/french";

import { Card, Eyebrow, SectionTitle } from "../ui/card";
import { ProgressBar } from "../ui/progress-bar";

const CRITERIA: Record<string, string> = {
  task: "Task fulfilment",
  coherence: "Coherence",
  vocabulary: "Vocabulary",
  grammar: "Grammar",
};

// The rubric's own anchors (grade_writing.md): each point on /5 stands for a level.
const LEVELS = ["below A1", "A1–A2", "B1", "B2", "C1–C2", "strong C2"];

function levelOf(score: number): string {
  const low = LEVELS[Math.floor(score)] ?? "";
  const high = LEVELS[Math.ceil(score)] ?? "";
  return low === high ? low : `${low} to ${high}`;
}

export function WritingFeedback({ result }: { result: Schemas["WritingResult"] }) {
  if (result.status === "pending") {
    return (
      <Card role="status" className="flex items-start gap-3 bg-accent-soft text-accent">
        <Clock className="mt-0.5 size-5 shrink-0" aria-hidden />
        <p className="text-sm">
          Saved. Grading is paused (budget cap reached or grader unavailable) and will run
          automatically when it can. Nothing is lost.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-4" role="status">
      <Card className="grid gap-6 sm:grid-cols-[auto_1fr] sm:items-center">
        <div className="text-center">
          <Eyebrow>TCF /20</Eyebrow>
          <p className="font-serif text-5xl font-semibold tabular-nums">{result.score}</p>
          <p className="text-xs text-muted">{result.word_count} words</p>
        </div>
        <div className="space-y-5">
          {Object.entries(CRITERIA).map(([key, label]) => {
            const score = result.criteria[key] ?? 0;
            const reason = result.reasons[key];
            const evidence = result.evidence[key];
            return (
              <div key={key}>
                <div className="mb-1 flex justify-between gap-2 text-sm">
                  <span>{label}</span>
                  <span className="text-muted tabular-nums">
                    {score} / 5 · {levelOf(score)}
                  </span>
                </div>
                <ProgressBar value={(score / 5) * 100} label={label} />
                {reason && <p className="mt-2 text-sm text-muted">{reason}</p>}
                {reason && evidence && (
                  <p
                    lang="fr"
                    className="mt-1 border-l-2 border-line pl-2 text-sm text-muted italic"
                  >
                    {fr(evidence)}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </Card>

      {result.fixes.length > 0 && (
        <Card className="space-y-3">
          <SectionTitle>Fix these first</SectionTitle>
          <ol className="space-y-3">
            {result.fixes.map((fix, i) => (
              <li key={i} className="rounded-xl border border-line p-3">
                <p lang="fr" className="flex flex-wrap items-center gap-2">
                  <span className="text-danger line-through">{fr(fix.excerpt)}</span>
                  <ArrowRight className="size-4 text-muted" aria-hidden />
                  <span className="font-medium text-success">{fr(fix.correction)}</span>
                </p>
                <p className="mt-1 text-sm text-muted">{fix.explanation}</p>
              </li>
            ))}
          </ol>
          <p className="text-sm text-muted">Rewrite your text with these fixes before moving on.</p>
        </Card>
      )}
    </div>
  );
}
