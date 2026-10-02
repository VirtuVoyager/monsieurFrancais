"use client";

import { Loader2, Mic, PhoneOff } from "lucide-react";
import { useState } from "react";

import { Glossed } from "@/components/glossary/glossed";
import { Clock, useCountdown } from "@/components/exam/countdown";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, Eyebrow, SectionTitle } from "@/components/ui/card";
import { cx } from "@/components/ui/cx";
import { ErrorState, Loading } from "@/components/ui/states";
import { WritingFeedback } from "@/components/writing/writing-feedback";
import type { Schemas } from "@/lib/api/client";
import { fr } from "@/lib/french";
import { useSpeakingTasks, useStartSpeaking } from "@/lib/queries";
import { useExaminerCall } from "@/lib/realtime";

type Session = Schemas["SpeakingSessionOut"];
type Pace = Schemas["SpeakingStart"]["pace"] & string;

const PACES: { value: Pace; label: string; detail: string }[] = [
  { value: "slow", label: "Slow", detail: "0.75×" },
  { value: "learner", label: "Learner", detail: "0.9×" },
  { value: "exam", label: "Exam", detail: "1.0×, real test speed" },
];

function minutes(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s ? `${m} min ${s} s` : `${m} min`;
}

export function SpeakingPage() {
  const tasks = useSpeakingTasks();
  const start = useStartSpeaking();
  const [pace, setPace] = useState<Pace>("learner");
  const [showTranscript, setShowTranscript] = useState(true);
  const session = start.data;
  const exam = pace === "exam" && !showTranscript;

  return (
    <div className="space-y-6">
      <header>
        <Eyebrow>Live examiner · graded on /20</Eyebrow>
        <h1 className="mt-1 font-serif text-3xl font-semibold" lang="fr">
          Expression orale
        </h1>
      </header>

      {tasks.isPending && <Loading />}
      {tasks.isError && <ErrorState error={tasks.error} />}
      {start.isError && <ErrorState error={start.error} />}
      {tasks.data && !session && (
        <>
          <Card className="space-y-4">
            <div className="space-y-2">
              <p className="text-sm font-medium">Examiner&apos;s speed</p>
              <div role="radiogroup" aria-label="Examiner's speed" className="flex flex-wrap gap-2">
                {PACES.map((p) => (
                  <button
                    key={p.value}
                    type="button"
                    role="radio"
                    aria-checked={pace === p.value}
                    onClick={() => setPace(p.value)}
                    className={cx(
                      "rounded-xl border px-3 py-2 text-left text-sm transition-colors",
                      pace === p.value
                        ? "border-accent bg-accent-soft text-accent"
                        : "border-line hover:bg-surface-2",
                    )}
                  >
                    <span className="font-medium">{p.label}</span>{" "}
                    <span className="text-muted">{p.detail}</span>
                  </button>
                ))}
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={showTranscript}
                onChange={(e) => setShowTranscript(e.target.checked)}
              />
              Show the examiner&apos;s words while speaking
            </label>
            <p className="text-sm text-muted">
              {exam
                ? "Exam conditions: this session counts towards your speaking level."
                : "Practice: graded, but only Exam speed with the words hidden counts towards your speaking level."}
            </p>
          </Card>
          <div className="grid gap-4 sm:grid-cols-3">
            {tasks.data.map((t) => (
              <Card key={t.code} className="flex flex-col justify-between gap-4">
                <div>
                  <p className="text-sm text-muted">Tâche {t.code.slice(2)}</p>
                  <SectionTitle lang="fr">{t.title}</SectionTitle>
                  <p className="mt-1 text-sm text-muted">
                    {t.prep_seconds ? `${minutes(t.prep_seconds)} to prepare, then ` : ""}
                    {minutes(t.seconds)}
                  </p>
                </div>
                <Button
                  onClick={() =>
                    start.mutate({ task: t.code, pace, show_transcript: showTranscript })
                  }
                  disabled={start.isPending}
                >
                  Start
                </Button>
              </Card>
            ))}
          </div>
          <p className="text-sm text-muted">
            A voice examiner runs the task in French, in real time; your answers are recorded,
            transcribed and graded when you finish. Use headphones. A session costs a few cents.
          </p>
        </>
      )}
      {session && (
        <Task
          key={session.run_id}
          session={session}
          showTranscript={showTranscript}
          onDone={() => start.reset()}
        />
      )}
    </div>
  );
}

function Task({
  session,
  showTranscript,
  onDone,
}: {
  session: Session;
  showTranscript: boolean;
  onDone: () => void;
}) {
  const [ready, setReady] = useState(session.task.prep_seconds === 0);
  return (
    <div className="space-y-4">
      <Card className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm text-muted" lang="fr">
            Tâche {session.task.code.slice(2)} · {session.task.title}
          </p>
          <Badge tone={session.exam ? "accent" : "neutral"}>
            {session.exam ? "Exam conditions" : "Practice"}
          </Badge>
        </div>
        <p lang="fr" className="leading-relaxed">
          {fr(session.prompt)}
        </p>
      </Card>
      {ready ? (
        <Call runId={session.run_id} showTranscript={showTranscript} onDone={onDone} />
      ) : (
        <Preparation seconds={session.task.prep_seconds} onReady={() => setReady(true)} />
      )}
    </div>
  );
}

function Preparation({ seconds, onReady }: { seconds: number; onReady: () => void }) {
  const [deadline] = useState(() => new Date(Date.now() + seconds * 1000).toISOString());
  const remaining = useCountdown(deadline, onReady);
  return (
    <Card className="flex items-center justify-between gap-4">
      <p>
        Preparation <Clock remaining={remaining} />
      </p>
      <Button variant="secondary" onClick={onReady}>
        I&apos;m ready
      </Button>
    </Card>
  );
}

function Call({
  runId,
  showTranscript,
  onDone,
}: {
  runId: number;
  showTranscript: boolean;
  onDone: () => void;
}) {
  const call = useExaminerCall(runId);

  if (call.state === "grading") {
    return (
      <Card role="status" className="flex items-center gap-3">
        <Loader2 className="size-5 animate-spin text-accent" aria-hidden />
        Transcribing and grading your answers…
      </Card>
    );
  }
  if (call.state === "ended") {
    return (
      <div className="space-y-4">
        {call.error && <ErrorState error={call.error} />}
        {call.result ? (
          <Glossed>
            <Result runId={runId} result={call.result} />
          </Glossed>
        ) : null}
        <Button variant="secondary" onClick={onDone}>
          Choose another task
        </Button>
      </div>
    );
  }
  return (
    <div className="space-y-4">
      <Card className="flex items-center justify-between gap-4">
        {call.state === "idle" && (
          <>
            <p className="text-sm text-muted">
              The clock starts when the examiner connects and can&apos;t be paused.
            </p>
            <Button onClick={() => void call.start()}>
              <Mic className="size-4" aria-hidden />
              Begin
            </Button>
          </>
        )}
        {call.state === "connecting" && <p className="text-muted">Connecting…</p>}
        {call.state === "live" && call.deadline && (
          <LiveBar deadline={call.deadline} onEnd={() => void call.end()} />
        )}
      </Card>
      {showTranscript && <Transcript lines={call.lines} />}
    </div>
  );
}

function LiveBar({ deadline, onEnd }: { deadline: string; onEnd: () => void }) {
  const remaining = useCountdown(deadline, onEnd);
  return (
    <>
      <span className="flex items-center gap-2 text-sm font-medium">
        <span className="size-2 animate-pulse rounded-full bg-danger" aria-hidden />
        Live <Clock remaining={remaining} />
      </span>
      <Button variant="secondary" onClick={onEnd}>
        <PhoneOff className="size-4" aria-hidden />
        End
      </Button>
    </>
  );
}

function Result({ runId, result }: { runId: number; result: Schemas["SpeakingResult"] }) {
  return (
    <div className="space-y-4">
      {result.status === "empty" && (
        <Card>
          No answer was heard, so there is nothing to grade. Check that your microphone works and
          speak after the examiner&apos;s question.
        </Card>
      )}
      {result.status === "pending" && (
        <Card role="status" className="bg-accent-soft text-accent">
          Saved. Grading is paused (budget cap reached or a provider unavailable) and will run
          automatically within 10 minutes; the fixes will then join your error list.
        </Card>
      )}
      {result.feedback && <WritingFeedback result={result.feedback} />}
      {result.level && (
        <Card className="text-center text-muted">
          Speaking level now estimated at {Math.round(result.level.score)}/20 · {result.level.cefr}
          {result.level.nclc !== null ? ` · NCLC ${result.level.nclc}` : ""}
        </Card>
      )}
      {result.has_recording && (
        <Card className="space-y-2">
          <SectionTitle>Your recording</SectionTitle>
          <audio controls src={`/api/speaking/sessions/${runId}/recording`} className="w-full" />
        </Card>
      )}
      <Transcript lines={result.transcript} />
    </div>
  );
}

function Transcript({ lines }: { lines: Schemas["TranscriptLine"][] }) {
  if (lines.length === 0) return null;
  return (
    <Card className="space-y-2" aria-label="Transcript">
      {lines.map((line, i) => (
        <p key={i} lang="fr" className="text-sm leading-relaxed">
          <span className={line.role === "candidate" ? "font-medium text-accent" : "text-muted"}>
            {line.role === "candidate" ? "Vous" : "Examinateur"} ·{" "}
          </span>
          {fr(line.text)}
        </p>
      ))}
    </Card>
  );
}
