"use client";

import { ArrowLeft, Loader2, Mic, Snail, Square, Volume2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Glossed } from "@/components/glossary/glossed";
import { Badge } from "@/components/ui/badge";
import { Button, ButtonLink } from "@/components/ui/button";
import { Card, Eyebrow, SectionTitle } from "@/components/ui/card";
import { cx } from "@/components/ui/cx";
import { ErrorState, Loading } from "@/components/ui/states";
import type { Schemas } from "@/lib/api/client";
import { fr } from "@/lib/french";
import { useRepeatAttempt, useRepeatSet, useRepeatSets } from "@/lib/queries";
import { useRecorder } from "@/lib/recorder";
import { speakFrench } from "@/lib/speech";
import { toWav } from "@/lib/wav";

type Sentence = Schemas["RepeatSentenceOut"];
type Result = Schemas["RepeatAttemptOut"];
type Outcome = { sentence: Sentence; attempts: number; passed: boolean; weak: string[] };

const SLOW_RATE = 0.7;

export function RepeatSetsPage() {
  const sets = useRepeatSets();
  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <Link href="/speak" className="inline-flex items-center gap-1 text-sm text-muted">
          <ArrowLeft className="size-4" aria-hidden /> Expression orale
        </Link>
        <Eyebrow>Pronunciation coach</Eyebrow>
        <h1 className="font-serif text-3xl font-semibold">Repeat after me</h1>
        <p className="text-muted">
          Listen to a sentence, say it, and get told exactly which words to fix. Three tries per
          sentence, then the next one.
        </p>
      </header>
      {sets.isPending && <Loading />}
      {sets.isError && <ErrorState error={sets.error} />}
      <div className="grid gap-4 sm:grid-cols-3">
        {sets.data?.map((s) => (
          <Card key={s.id} className="flex flex-col justify-between gap-4">
            <div className="space-y-1">
              <Badge>{s.cefr}</Badge>
              <SectionTitle lang="fr">{s.title}</SectionTitle>
              <p className="text-sm text-muted">{s.focus}</p>
            </div>
            <ButtonLink href={`/speak/repeat/${s.id}`}>{s.sentences} sentences</ButtonLink>
          </Card>
        ))}
      </div>
      <p className="text-sm text-muted">
        Use headphones or a quiet room. Each try is scored by Azure pronunciation assessment and
        costs a fraction of a cent; a correction from the coach only runs when something needs
        fixing.
      </p>
    </div>
  );
}

export function RepeatPlayerPage({ id }: { id: string }) {
  const set = useRepeatSet(id);
  if (set.isPending) return <Loading />;
  if (set.isError) return <ErrorState error={set.error} />;
  return (
    <Glossed>
      <Player detail={set.data} />
    </Glossed>
  );
}

function Player({ detail }: { detail: Schemas["RepeatSetDetail"] }) {
  const [outcomes, setOutcomes] = useState<Outcome[]>([]);
  const index = outcomes.length;
  const sentence = detail.sentences[index];

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <Link href="/speak/repeat" className="inline-flex items-center gap-1 text-sm text-muted">
          <ArrowLeft className="size-4" aria-hidden /> Repeat after me
        </Link>
        <Eyebrow>
          {sentence ? `Sentence ${index + 1} of ${detail.sentences.length}` : "Done"}
        </Eyebrow>
        <h1 className="font-serif text-2xl font-semibold" lang="fr">
          {detail.title}
        </h1>
      </header>
      {sentence ? (
        <Attempts
          key={sentence.id}
          sentence={sentence}
          maxAttempts={detail.max_attempts}
          maxSeconds={detail.max_seconds}
          onDone={(outcome) => setOutcomes((all) => [...all, outcome])}
        />
      ) : (
        <Summary outcomes={outcomes} onRestart={() => setOutcomes([])} />
      )}
    </div>
  );
}

function Attempts({
  sentence,
  maxAttempts,
  maxSeconds,
  onDone,
}: {
  sentence: Sentence;
  maxAttempts: number;
  maxSeconds: number;
  onDone: (outcome: Outcome) => void;
}) {
  const recorder = useRecorder(maxSeconds);
  const submit = useRepeatAttempt();
  const [attempt, setAttempt] = useState(1);
  const [result, setResult] = useState<Result | null>(null);
  const [mine, setMine] = useState<string | null>(null);
  const [micError, setMicError] = useState<Error | null>(null);
  const finished = result?.status === "passed" || result?.status === "next";

  useEffect(() => () => void (mine && URL.revokeObjectURL(mine)), [mine]);

  const play = (rate: number) => {
    if (!sentence.audio_url) return speakFrench(sentence.fr, rate * 0.95);
    const audio = new Audio(sentence.audio_url);
    audio.playbackRate = rate;
    void audio.play();
  };

  const take = async () => {
    setMicError(null);
    let recording: Blob;
    try {
      recording = await recorder.record();
    } catch {
      setMicError(new Error("The microphone isn't available. Allow access and try again."));
      return;
    }
    setMine(URL.createObjectURL(recording));
    let wav: Blob;
    try {
      wav = await toWav(recording);
    } catch {
      setMicError(new Error("That recording couldn't be read. Try again, a little longer."));
      return;
    }
    submit.mutate(
      { sentenceId: sentence.id, attempt, wav },
      {
        onSuccess: (scored) => {
          setResult(scored);
          if (scored.status === "retry") setAttempt(attempt + 1);
        },
      },
    );
  };

  const next = () =>
    result &&
    onDone({
      sentence,
      attempts: result.attempt,
      passed: result.status === "passed",
      weak: result.words.filter((w) => w.weak).map((w) => w.word),
    });

  return (
    <div className="space-y-4">
      <Card className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <Badge tone="accent">
            Try {Math.min(attempt, maxAttempts)} of {maxAttempts}
          </Badge>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => play(1)} aria-label="Listen">
              <Volume2 className="size-4" aria-hidden /> Listen
            </Button>
            <Button variant="secondary" onClick={() => play(SLOW_RATE)} aria-label="Listen slowly">
              <Snail className="size-4" aria-hidden /> Slow
            </Button>
          </div>
        </div>
        {result && result.words.length > 0 ? (
          <Marked words={result.words} />
        ) : (
          <p lang="fr" className="font-serif text-2xl leading-relaxed">
            {fr(sentence.fr)}
          </p>
        )}
        <p className="text-sm text-muted">{sentence.en}</p>
        <p className="rounded-xl bg-surface-2 p-3 text-sm">{sentence.tip}</p>
      </Card>

      {result && <Feedback result={result} />}
      {submit.isError && <ErrorState error={submit.error} />}
      {micError && <ErrorState error={micError} />}

      <div className="flex flex-wrap items-center gap-3">
        {finished ? (
          <Button onClick={next}>Next sentence</Button>
        ) : recorder.recording ? (
          <Button onClick={recorder.stop}>
            <Square className="size-4" aria-hidden /> Stop
          </Button>
        ) : (
          <Button onClick={() => void take()} disabled={submit.isPending}>
            {submit.isPending ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <Mic className="size-4" aria-hidden />
            )}
            {submit.isPending ? "Listening to you…" : result ? "Say it again" : "Record"}
          </Button>
        )}
        {recorder.recording && (
          <span className="flex items-center gap-2 text-sm text-muted" role="status">
            <span className="size-2 animate-pulse rounded-full bg-danger" aria-hidden />
            Recording, stops by itself after {maxSeconds} s
          </span>
        )}
        {mine && !recorder.recording && (
          <audio controls src={mine} className="h-9" aria-label="Your last try" />
        )}
      </div>
    </div>
  );
}

function Marked({ words }: { words: Schemas["RepeatWordOut"][] }) {
  return (
    <p lang="fr" className="font-serif text-2xl leading-relaxed">
      {words.map((w, i) => (
        <span key={i}>
          <span
            className={cx(
              w.weak ? "text-danger underline decoration-wavy underline-offset-4" : "text-success",
            )}
          >
            {fr(w.word)}
          </span>{" "}
        </span>
      ))}
    </p>
  );
}

function Feedback({ result }: { result: Result }) {
  if (result.status === "unheard") {
    return (
      <Card role="status">
        I couldn&apos;t hear the whole sentence. Check your microphone, then say all of it. This
        didn&apos;t use up a try.
      </Card>
    );
  }
  if (result.status === "passed") {
    return (
      <Card role="status" className="bg-success-soft text-success">
        <span lang="fr">Bien prononcé !</span> Every word came through clearly.
      </Card>
    );
  }
  return (
    <Card role="status" className="space-y-2">
      <p className="leading-relaxed">{fr(result.feedback)}</p>
      {result.status === "next" && (
        <p className="text-sm text-muted">
          That was the last try for this sentence. It goes on your list to practise.
        </p>
      )}
    </Card>
  );
}

function Summary({ outcomes, onRestart }: { outcomes: Outcome[]; onRestart: () => void }) {
  const firstTry = outcomes.filter((o) => o.passed && o.attempts === 1).length;
  const practise = outcomes.filter((o) => !o.passed);
  return (
    <div className="space-y-4">
      <Card className="space-y-1">
        <SectionTitle>
          {firstTry} of {outcomes.length} right first time
        </SectionTitle>
        <p className="text-sm text-muted">
          {outcomes.length - firstTry - practise.length} after a correction, {practise.length} to
          practise.
        </p>
      </Card>
      {practise.length > 0 && (
        <Card className="space-y-3">
          <SectionTitle>Keep practising</SectionTitle>
          <ul className="space-y-2">
            {practise.map((o) => (
              <li key={o.sentence.id} lang="fr">
                {fr(o.sentence.fr)}
                {o.weak.length > 0 && (
                  <span className="text-sm text-danger"> · {o.weak.join(", ")}</span>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}
      <div className="flex gap-2">
        <Button onClick={onRestart}>Go again</Button>
        <ButtonLink href="/speak/repeat" variant="secondary">
          Other sets
        </ButtonLink>
      </div>
    </div>
  );
}
