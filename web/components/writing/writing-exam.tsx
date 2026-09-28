"use client";

import { useCallback, useRef, useState } from "react";

import type { Schemas } from "@/lib/api/client";
import { fr } from "@/lib/french";

import { Clock, useCountdown } from "../exam/countdown";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { WritingEditor } from "./writing-editor";

/** Exam conditions for expression écrite: no templates, and time running out submits the text. */
export function WritingExam({
  drill,
  onSubmit,
  submitting,
}: {
  drill: Schemas["WritingDrillOut"];
  onSubmit: (text: string) => void;
  submitting: boolean;
}) {
  const [text, setText] = useState("");
  const submitted = useRef(false);

  const submit = useCallback(() => {
    if (submitted.current) return;
    submitted.current = true;
    onSubmit(text);
  }, [onSubmit, text]);
  const remaining = useCountdown(drill.deadline, submit);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted">Tâche {drill.task}</span>
        <Clock remaining={remaining} />
      </div>
      <Card className="space-y-4">
        <p lang="fr" className="leading-relaxed">
          {fr(drill.prompt)}
        </p>
        <WritingEditor
          value={text}
          onChange={setText}
          minWords={drill.min_words}
          maxWords={drill.max_words}
          disabled={submitting}
        />
      </Card>
      <div className="flex justify-end">
        <Button onClick={submit} disabled={submitting || !text.trim()}>
          Submit
        </Button>
      </div>
    </div>
  );
}
