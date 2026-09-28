"use client";

import { Check, RotateCcw, X } from "lucide-react";
import { useState } from "react";

import type { Schemas } from "@/lib/api/client";
import { fr } from "@/lib/french";

import { Button } from "../ui/button";
import { cx } from "../ui/cx";

export type ExerciseResponse = { choice?: number; text?: string };
type Result = Pick<Schemas["CheckResultOut"], "correct" | "expected" | "explanation">;

/** A single exercise. `onCheck` resolves with the verdict when feedback is immediate. */
export function Exercise({
  exercise,
  number,
  onCheck,
  onChange,
}: {
  exercise: Schemas["ExerciseOut"];
  number: number;
  onCheck?: (response: ExerciseResponse) => Promise<Result>;
  onChange?: (response: ExerciseResponse) => void;
}) {
  const [response, setResponse] = useState<ExerciseResponse>({});
  const [result, setResult] = useState<Result | null>(null);
  const [pending, setPending] = useState(false);

  const update = (next: ExerciseResponse) => {
    setResponse(next);
    onChange?.(next);
  };

  const submit = async () => {
    if (!onCheck) return;
    setPending(true);
    try {
      setResult(await onCheck(response));
    } finally {
      setPending(false);
    }
  };

  const answered = response.choice !== undefined || Boolean(response.text?.trim());

  return (
    <div className="rounded-xl border border-line p-4">
      <p className="mb-3 font-medium" lang="fr">
        <span className="mr-2 text-muted tabular-nums">{number}.</span>
        {exercise.kind === "order" ? "Put the words in order." : fr(exercise.prompt ?? "")}
      </p>

      {exercise.kind === "mcq" && (
        <div role="radiogroup" className="grid gap-2 sm:grid-cols-3">
          {exercise.options?.map((option, index) => (
            <button
              key={option}
              type="button"
              role="radio"
              aria-checked={response.choice === index}
              disabled={result !== null}
              onClick={() => update({ choice: index })}
              lang="fr"
              className={cx(
                "rounded-lg border px-3 py-2 text-left text-sm transition-colors",
                response.choice === index
                  ? "border-accent bg-accent-soft text-accent"
                  : "border-line hover:bg-surface-2",
              )}
            >
              {fr(option)}
            </button>
          ))}
        </div>
      )}

      {exercise.kind === "cloze" && (
        <input
          lang="fr"
          aria-label={`Answer for question ${number}`}
          autoComplete="off"
          spellCheck={false}
          disabled={result !== null}
          value={response.text ?? ""}
          onChange={(e) => update({ text: e.target.value })}
          onKeyDown={(e) => e.key === "Enter" && answered && void submit()}
          className="w-full rounded-lg border border-line bg-surface px-3 py-2 outline-none focus:border-accent sm:w-64"
        />
      )}

      {exercise.kind === "order" && (
        <WordOrder
          words={exercise.words ?? []}
          disabled={result !== null}
          onChange={(text) => update({ text })}
        />
      )}

      {onCheck && (
        <div className="mt-3 flex items-center gap-3">
          {result === null ? (
            <Button variant="secondary" disabled={!answered || pending} onClick={submit}>
              Check
            </Button>
          ) : (
            <Feedback result={result} />
          )}
        </div>
      )}
    </div>
  );
}

function Feedback({ result }: { result: Result }) {
  return (
    <div
      role="status"
      className={cx(
        "flex w-full items-start gap-2 rounded-lg px-3 py-2 text-sm",
        result.correct ? "bg-success-soft text-success" : "bg-danger-soft text-danger",
      )}
    >
      {result.correct ? (
        <Check className="mt-0.5 size-4 shrink-0" aria-hidden />
      ) : (
        <X className="mt-0.5 size-4 shrink-0" aria-hidden />
      )}
      <div lang="fr">
        <p className="font-medium">
          {result.correct ? "Correct" : <>Answer: {fr(result.expected)}</>}
        </p>
        {result.explanation && <p className="mt-0.5 opacity-90">{fr(result.explanation)}</p>}
      </div>
    </div>
  );
}

function WordOrder({
  words,
  disabled,
  onChange,
}: {
  words: string[];
  disabled: boolean;
  onChange: (text: string) => void;
}) {
  const [picked, setPicked] = useState<number[]>([]);

  const choose = (next: number[]) => {
    setPicked(next);
    onChange(next.map((i) => words[i]).join(" "));
  };

  return (
    <div className="space-y-3" lang="fr">
      <div className="flex min-h-11 flex-wrap items-center gap-2 rounded-lg border border-dashed border-line p-2">
        {picked.length === 0 && <span className="text-sm text-muted">Tap words below</span>}
        {picked.map((i) => (
          <span key={i} className="rounded-md bg-accent-soft px-2 py-1 text-sm text-accent">
            {words[i]}
          </span>
        ))}
        {picked.length > 0 && !disabled && (
          <button
            type="button"
            aria-label="Clear"
            onClick={() => choose([])}
            className="ml-auto text-muted hover:text-ink"
          >
            <RotateCcw className="size-4" />
          </button>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        {words.map((word, i) => (
          <button
            key={`${word}-${i}`}
            type="button"
            disabled={disabled || picked.includes(i)}
            onClick={() => choose([...picked, i])}
            className="rounded-md border border-line px-2 py-1 text-sm hover:bg-surface-2 disabled:opacity-30"
          >
            {word}
          </button>
        ))}
      </div>
    </div>
  );
}
