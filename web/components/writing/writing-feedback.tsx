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
        <div className="space-y-3">
          {Object.entries(CRITERIA).map(([key, label]) => (
            <div key={key}>
              <div className="mb-1 flex justify-between text-sm">
                <span>{label}</span>
                <span className="text-muted tabular-nums">{result.criteria[key] ?? 0} / 5</span>
              </div>
              <ProgressBar value={((result.criteria[key] ?? 0) / 5) * 100} label={label} />
            </div>
          ))}
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
