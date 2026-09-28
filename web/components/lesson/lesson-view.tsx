"use client";

import { Eye, EyeOff, Play } from "lucide-react";
import { useEffect, useState } from "react";

import type { Schemas } from "@/lib/api/client";
import { fr } from "@/lib/french";
import { useCheckExercise } from "@/lib/queries";
import { speakFrench } from "@/lib/speech";

import { Exercise } from "../exercise/exercise";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { cx } from "../ui/cx";
import { FrenchMarkdown } from "../ui/markdown";
import { GenderTag } from "./gender-tag";
import { SpeakButton } from "./speak-button";

type Lesson = Schemas["LessonOut"];

export function LessonView({ lesson }: { lesson: Lesson }) {
  const { content } = lesson;
  switch (content.kind) {
    case "grammar":
      return (
        <div className="space-y-6">
          <Card>
            <h2 className="mb-4 font-serif text-xl font-semibold" lang="fr">
              {fr(content.concept_title)}
            </h2>
            <FrenchMarkdown>{content.concept_md}</FrenchMarkdown>
          </Card>
          <Exercises lessonId={lesson.id} exercises={content.exercises} />
        </div>
      );
    case "vocab":
      return <WordList words={content.words} />;
    case "sentences":
      return <SentenceList sentences={content.sentences} />;
    case "listening":
      return <Listening lessonId={lesson.id} content={content} />;
    case "reading":
      return (
        <div className="space-y-6">
          <Card>
            <p lang="fr" className="leading-relaxed whitespace-pre-line">
              {fr(content.text)}
            </p>
          </Card>
          <Exercises lessonId={lesson.id} exercises={content.exercises} />
        </div>
      );
    case "writing":
      return <Writing content={content} lessonId={lesson.id} />;
    case "speaking":
      return <Speaking content={content} />;
  }
}

function Exercises({
  lessonId,
  exercises,
}: {
  lessonId: string;
  exercises: Schemas["ExerciseOut"][];
}) {
  const check = useCheckExercise(lessonId);
  if (exercises.length === 0) return null;
  return (
    <Card className="space-y-4">
      <h2 className="font-serif text-lg font-semibold">Practice</h2>
      {exercises.map((exercise, index) => (
        <Exercise
          key={index}
          number={index + 1}
          exercise={exercise}
          onCheck={(response) => check.mutateAsync({ index, response })}
        />
      ))}
    </Card>
  );
}

function WordList({ words }: { words: Schemas["WordOut"][] }) {
  const [showEnglish, setShowEnglish] = useState(true);
  return (
    <Card>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-muted">
          Say each word aloud with its article. Cards go into your review queue when you finish.
        </p>
        <Button variant="ghost" onClick={() => setShowEnglish(!showEnglish)}>
          {showEnglish ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
          English
        </Button>
      </div>
      <ul className="divide-y divide-line">
        {words.map((word) => (
          <li key={word.id} className="flex items-start gap-3 py-3">
            <SpeakButton text={word.lemma} />
            <div className="min-w-0 flex-1">
              <p className="flex flex-wrap items-center gap-2">
                <span lang="fr" className="font-medium">
                  {fr(word.lemma)}
                </span>
                <GenderTag gender={word.gender} />
                <span className="text-xs text-muted">{word.pos}</span>
              </p>
              {showEnglish && <p className="text-sm text-muted">{word.en}</p>}
              <p lang="fr" className="mt-1 text-sm italic">
                {fr(word.example_fr)}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function SentenceList({ sentences }: { sentences: Schemas["SentenceOut"][] }) {
  const [revealed, setRevealed] = useState<Set<string>>(new Set());
  const toggle = (id: string) =>
    setRevealed((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  return (
    <Card>
      <p className="mb-4 text-sm text-muted">
        Read each sentence aloud, then shadow it: play it and speak along at the same time.
      </p>
      <ul className="space-y-3">
        {sentences.map((s) => (
          <li key={s.id} className="flex items-start gap-3 rounded-xl border border-line p-3">
            <SpeakButton text={s.fr} />
            <button type="button" className="flex-1 text-left" onClick={() => toggle(s.id)}>
              <p lang="fr">{fr(s.fr)}</p>
              <p className={cx("text-sm text-muted", !revealed.has(s.id) && "sr-only")}>{s.en}</p>
            </button>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function Listening({
  lessonId,
  content,
}: {
  lessonId: string;
  content: Schemas["ListeningContent"];
}) {
  const [showTranscript, setShowTranscript] = useState(false);
  return (
    <div className="space-y-6">
      <Card className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={() => speakFrench(content.transcript, 0.9)}>
            <Play className="size-4" aria-hidden /> Play audio
          </Button>
          <Button variant="ghost" onClick={() => setShowTranscript(!showTranscript)}>
            {showTranscript ? "Hide" : "Show"} transcript
          </Button>
        </div>
        <p className="text-xs text-muted">
          Practice mode uses your browser&apos;s French voice until the recorded audio is generated.
          Timed assessments play recorded audio once.
        </p>
        {showTranscript && (
          <p lang="fr" className="rounded-xl bg-surface-2 p-4 leading-relaxed">
            {fr(content.transcript)}
          </p>
        )}
      </Card>
      <Exercises lessonId={lessonId} exercises={content.exercises} />
    </div>
  );
}

function Writing({ content, lessonId }: { content: Schemas["WritingContent"]; lessonId: string }) {
  const storageKey = `draft:${lessonId}`;
  // Lessons load client-side, so this never runs during server rendering.
  const [text, setText] = useState(() => localStorage.getItem(storageKey) ?? "");
  useEffect(() => {
    const id = setTimeout(() => localStorage.setItem(storageKey, text), 500);
    return () => clearTimeout(id);
  }, [storageKey, text]);

  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  const inRange = words >= content.min_words && words <= content.max_words;
  return (
    <Card className="space-y-4">
      <p className="text-xs font-semibold text-muted uppercase">Tâche {content.task}</p>
      <p lang="fr" className="leading-relaxed">
        {fr(content.prompt)}
      </p>
      <textarea
        lang="fr"
        aria-label="Your answer"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={8}
        className="w-full rounded-xl border border-line bg-surface p-3 leading-relaxed outline-none focus:border-accent"
      />
      <div className="flex items-center justify-between text-sm">
        <span className={cx("tabular-nums", inRange ? "text-success" : "text-muted")}>
          {words} words · target {content.min_words}–{content.max_words}
        </span>
        <span className="text-xs text-muted">Draft saved on this device</span>
      </div>
      <p className="rounded-xl bg-accent-soft p-3 text-sm text-accent">
        Rubric grading (TCF /20, top 3 fixes) switches on once the Azure grader is connected.
      </p>
    </Card>
  );
}

function Speaking({ content }: { content: Schemas["SpeakingContent"] }) {
  const [remaining, setRemaining] = useState<number | null>(null);
  useEffect(() => {
    if (remaining === null || remaining <= 0) return;
    const id = setTimeout(() => setRemaining(remaining - 1), 1000);
    return () => clearTimeout(id);
  }, [remaining]);
  return (
    <Card className="space-y-4">
      <p className="text-xs font-semibold text-muted uppercase">Tâche {content.task}</p>
      <p lang="fr" className="leading-relaxed">
        {fr(content.prompt)}
      </p>
      <div className="flex items-center gap-4">
        <Button onClick={() => setRemaining(content.seconds)}>
          {remaining === null ? "Start timer" : "Restart"}
        </Button>
        {remaining !== null && (
          <span className="font-serif text-3xl tabular-nums" aria-live="polite">
            {remaining > 0 ? `${remaining}s` : "Temps écoulé"}
          </span>
        )}
      </div>
      <p className="rounded-xl bg-accent-soft p-3 text-sm text-accent">
        Recording, transcription and pronunciation scoring switch on with Azure Speech. For now,
        speak aloud against the timer.
      </p>
    </Card>
  );
}
