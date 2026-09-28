"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { GenderTag } from "@/components/lesson/gender-tag";
import { SpeakButton } from "@/components/lesson/speak-button";
import { Button } from "@/components/ui/button";
import { Card, Eyebrow } from "@/components/ui/card";
import { Empty, ErrorState, Loading } from "@/components/ui/states";
import { fr } from "@/lib/french";
import { keys, useDueReviews, useRateCard } from "@/lib/queries";

const RATINGS = [
  { value: 1, label: "Again" },
  { value: 2, label: "Hard" },
  { value: 3, label: "Good" },
  { value: 4, label: "Easy" },
];

export function ReviewPage() {
  const due = useDueReviews();
  const rate = useRateCard();
  const queryClient = useQueryClient();
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);

  if (due.isPending) return <Loading />;
  if (due.isError) return <ErrorState error={due.error} />;

  const card = due.data[index];
  if (!card) {
    return (
      <div className="space-y-6">
        <h1 className="font-serif text-3xl font-semibold">Review</h1>
        <Empty title="Nothing due right now">
          Complete vocabulary and sentence lessons to add cards.
        </Empty>
      </div>
    );
  }

  const answer = async (rating: number) => {
    await rate.mutateAsync({ id: card.id, rating });
    setRevealed(false);
    if (index + 1 < due.data.length) setIndex(index + 1);
    else {
      setIndex(0);
      void queryClient.invalidateQueries({ queryKey: keys.due });
    }
  };

  return (
    <div className="space-y-6">
      <header className="flex items-baseline justify-between">
        <h1 className="font-serif text-3xl font-semibold">Review</h1>
        <span className="text-muted text-sm tabular-nums">
          {index + 1} / {due.data.length}
        </span>
      </header>
      <Card className="flex min-h-72 flex-col items-center justify-center gap-6 text-center">
        <Eyebrow>Say it in French, out loud</Eyebrow>
        <p className="font-serif text-2xl">{card.prompt_en}</p>
        {revealed ? (
          <div className="space-y-2" lang="fr">
            <p className="text-accent flex items-center justify-center gap-2 text-2xl font-semibold">
              {fr(card.answer_fr)} <GenderTag gender={card.gender} />
              <SpeakButton text={card.answer_fr} />
            </p>
            {card.example_fr && <p className="text-muted italic">{fr(card.example_fr)}</p>}
          </div>
        ) : (
          <Button onClick={() => setRevealed(true)}>Show answer</Button>
        )}
      </Card>
      {revealed && (
        <div
          className="grid grid-cols-4 gap-2"
          role="group"
          aria-label="How well did you recall it?"
        >
          {RATINGS.map((r) => (
            <Button
              key={r.value}
              variant="secondary"
              disabled={rate.isPending}
              onClick={() => answer(r.value)}
            >
              {r.label}
            </Button>
          ))}
        </div>
      )}
    </div>
  );
}
