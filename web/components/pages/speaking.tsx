"use client";

import { Mic, PhoneOff } from "lucide-react";
import { useState } from "react";

import { Clock, useCountdown } from "@/components/exam/countdown";
import { Button } from "@/components/ui/button";
import { Card, Eyebrow, SectionTitle } from "@/components/ui/card";
import { ErrorState, Loading } from "@/components/ui/states";
import type { Schemas } from "@/lib/api/client";
import { fr } from "@/lib/french";
import { useSpeakingTasks, useStartSpeaking } from "@/lib/queries";
import { useExaminerCall } from "@/lib/realtime";

type Session = Schemas["SpeakingSessionOut"];

function minutes(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s ? `${m} min ${s} s` : `${m} min`;
}

export function SpeakingPage() {
  const tasks = useSpeakingTasks();
  const start = useStartSpeaking();
  const session = start.data;

  return (
    <div className="space-y-6">
      <header>
        <Eyebrow>Live examiner · practice, not yet scored</Eyebrow>
        <h1 className="mt-1 font-serif text-3xl font-semibold" lang="fr">
          Expression orale
        </h1>
      </header>

      {tasks.isPending && <Loading />}
      {tasks.isError && <ErrorState error={tasks.error} />}
      {start.isError && <ErrorState error={start.error} />}
      {tasks.data && !session && (
        <>
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
                <Button onClick={() => start.mutate(t.code)} disabled={start.isPending}>
                  Start
                </Button>
              </Card>
            ))}
          </div>
          <p className="text-sm text-muted">
            A voice examiner runs the task in French, in real time. Use headphones. The session
            costs a few cents; its worst case is held against your budget until it ends.
          </p>
        </>
      )}
      {session && <Task key={session.run_id} session={session} onDone={() => start.reset()} />}
    </div>
  );
}

function Task({ session, onDone }: { session: Session; onDone: () => void }) {
  const [ready, setReady] = useState(session.task.prep_seconds === 0);
  return (
    <div className="space-y-4">
      <Card className="space-y-2">
        <p className="text-sm text-muted" lang="fr">
          Tâche {session.task.code.slice(2)} · {session.task.title}
        </p>
        <p lang="fr" className="leading-relaxed">
          {fr(session.prompt)}
        </p>
      </Card>
      {ready ? (
        <Call runId={session.run_id} onDone={onDone} />
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

function Call({ runId, onDone }: { runId: number; onDone: () => void }) {
  const call = useExaminerCall(runId);

  if (call.state === "ended") {
    return (
      <div className="space-y-4">
        {call.error && <ErrorState error={call.error} />}
        <Transcript lines={call.lines} />
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
      <Transcript lines={call.lines} />
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

function Transcript({ lines }: { lines: Schemas["TranscriptLine"][] }) {
  if (lines.length === 0) return null;
  return (
    <Card className="space-y-2" aria-label="Examiner transcript">
      {lines.map((line, i) => (
        <p key={i} lang="fr" className="text-sm leading-relaxed">
          <span className="text-muted">Examinateur · </span>
          {fr(line.text)}
        </p>
      ))}
    </Card>
  );
}
