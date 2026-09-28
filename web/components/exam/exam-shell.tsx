"use client";

import { Play, Timer } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import type { Schemas } from "@/lib/api/client";
import { fr } from "@/lib/french";
import { speakFrench } from "@/lib/speech";

import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { cx } from "../ui/cx";

type Answer = Schemas["ItemAnswer"];

/**
 * Exam conditions: one question at a time, no going back, audio plays once, and the
 * server's deadline is final. Time running out submits whatever has been answered.
 */
export function ExamShell({
  items,
  deadline,
  onSubmit,
  submitting,
}: {
  items: Schemas["CheckItemOut"][];
  deadline: string;
  onSubmit: (answers: Answer[]) => void;
  submitting: boolean;
}) {
  const [index, setIndex] = useState(0);
  const [choices, setChoices] = useState<Record<string, number>>({});
  const [remaining, setRemaining] = useState<number | null>(null);
  const shownAt = useRef<Record<string, number>>({});
  const timings = useRef<Record<string, number>>({});
  const submitted = useRef(false);

  const submit = useCallback(() => {
    if (submitted.current) return;
    submitted.current = true;
    onSubmit(
      Object.entries(choices).map(([item_id, choice]) => ({
        item_id,
        response: { choice },
        time_ms: timings.current[item_id] ?? null,
      })),
    );
  }, [choices, onSubmit]);

  useEffect(() => {
    const end = new Date(deadline).getTime();
    const id = setInterval(() => {
      const left = Math.max(Math.round((end - Date.now()) / 1000), 0);
      setRemaining(left);
      if (left === 0) submit();
    }, 250);
    return () => clearInterval(id);
  }, [deadline, submit]);

  const item = items[index];
  useEffect(() => {
    shownAt.current[item.id] ??= Date.now();
  }, [item.id]);

  const choose = (choice: number) => {
    setChoices({ ...choices, [item.id]: choice });
    timings.current[item.id] = Date.now() - (shownAt.current[item.id] ?? Date.now());
  };
  const last = index === items.length - 1;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted tabular-nums">
          Question {index + 1} / {items.length}
        </span>
        <span
          className={cx(
            "inline-flex items-center gap-1 font-medium tabular-nums",
            remaining !== null && remaining < 60 ? "text-danger" : "text-ink",
          )}
          aria-live="off"
        >
          <Timer className="size-4" aria-hidden />
          {remaining === null ? "–:–" : formatClock(remaining)}
        </span>
      </div>
      <Question key={item.id} item={item} choice={choices[item.id]} onChoose={choose} />
      <div className="flex justify-end">
        {last ? (
          <Button onClick={submit} disabled={submitting}>
            Submit
          </Button>
        ) : (
          <Button onClick={() => setIndex(index + 1)}>Next question</Button>
        )}
      </div>
    </div>
  );
}

function Question({
  item,
  choice,
  onChoose,
}: {
  item: Schemas["CheckItemOut"];
  choice: number | undefined;
  onChoose: (choice: number) => void;
}) {
  const { exercise } = item;
  const [played, setPlayed] = useState(false);
  const audio = useRef<HTMLAudioElement>(null);
  const hasAudio = Boolean(exercise.audio_url || exercise.audio_text);

  const play = () => {
    setPlayed(true);
    if (exercise.audio_url) void audio.current?.play();
    else if (exercise.audio_text) speakFrench(exercise.audio_text, 1);
  };

  return (
    <Card className="space-y-5">
      {hasAudio && (
        <div className="flex items-center gap-3">
          {exercise.audio_url && <audio ref={audio} src={exercise.audio_url} preload="auto" />}
          <Button onClick={play} disabled={played}>
            <Play className="size-4" aria-hidden /> {played ? "Played" : "Play once"}
          </Button>
          <span className="text-xs text-muted">The recording plays a single time.</span>
        </div>
      )}
      {exercise.passage && (
        <p lang="fr" className="rounded-xl bg-surface-2 p-4 leading-relaxed">
          {fr(exercise.passage)}
        </p>
      )}
      <p lang="fr" className="font-medium">
        {fr(exercise.prompt ?? "")}
      </p>
      <div role="radiogroup" className="grid gap-2">
        {exercise.options?.map((option, i) => (
          <button
            key={option}
            type="button"
            role="radio"
            aria-checked={choice === i}
            onClick={() => onChoose(i)}
            lang="fr"
            className={cx(
              "flex items-center gap-3 rounded-xl border px-4 py-3 text-left transition-colors",
              choice === i ? "border-accent bg-accent-soft" : "border-line hover:bg-surface-2",
            )}
          >
            <span className="grid size-6 shrink-0 place-items-center rounded-full border border-line text-xs font-semibold">
              {"ABCD"[i]}
            </span>
            {fr(option)}
          </button>
        ))}
      </div>
    </Card>
  );
}

function formatClock(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}
