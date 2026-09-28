"use client";

import { Search } from "lucide-react";
import { useDeferredValue, useState } from "react";

import { GenderTag } from "@/components/lesson/gender-tag";
import { SpeakButton } from "@/components/lesson/speak-button";
import { Card } from "@/components/ui/card";
import { cx } from "@/components/ui/cx";
import { FrenchMarkdown } from "@/components/ui/markdown";
import { Empty, ErrorState, Loading } from "@/components/ui/states";
import { fr } from "@/lib/french";
import { useLibraryConcepts, useLibrarySentences, useLibraryWords } from "@/lib/queries";

const TABS = ["Words", "Sentences", "Grammar"] as const;
type Tab = (typeof TABS)[number];

export function LibraryPage() {
  const [tab, setTab] = useState<Tab>("Words");
  const [query, setQuery] = useState("");
  const q = useDeferredValue(query.trim());

  return (
    <div className="space-y-6">
      <h1 className="font-serif text-3xl font-semibold">Library</h1>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div role="tablist" className="inline-flex rounded-xl border border-line bg-surface p-1">
          {TABS.map((t) => (
            <button
              key={t}
              role="tab"
              aria-selected={tab === t}
              onClick={() => setTab(t)}
              className={cx(
                "rounded-lg px-4 py-1.5 text-sm font-medium",
                tab === t ? "bg-accent-soft text-accent" : "text-muted hover:text-ink",
              )}
            >
              {t}
            </button>
          ))}
        </div>
        {tab !== "Grammar" && (
          <label className="relative block">
            <span className="sr-only">Search</span>
            <Search className="absolute top-2.5 left-3 size-4 text-muted" aria-hidden />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search French or English"
              className="w-full rounded-xl border border-line bg-surface py-2 pr-3 pl-9 text-sm outline-none focus:border-accent sm:w-72"
            />
          </label>
        )}
      </div>
      {tab === "Words" && <Words q={q} />}
      {tab === "Sentences" && <Sentences q={q} />}
      {tab === "Grammar" && <Concepts />}
    </div>
  );
}

function Words({ q }: { q: string }) {
  const words = useLibraryWords(q);
  if (words.isPending) return <Loading />;
  if (words.isError) return <ErrorState error={words.error} />;
  if (words.data.length === 0)
    return <Empty title="No words yet">Finish a vocabulary lesson.</Empty>;
  return (
    <Card className="p-0 sm:p-0">
      <ul className="divide-y divide-line">
        {words.data.map((w) => (
          <li key={w.id} className="flex items-center gap-3 px-5 py-3">
            <SpeakButton text={w.lemma} />
            <span lang="fr" className="font-medium">
              {fr(w.lemma)}
            </span>
            <GenderTag gender={w.gender} />
            <span className="ml-auto text-sm text-muted">{w.en}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function Sentences({ q }: { q: string }) {
  const sentences = useLibrarySentences(q);
  if (sentences.isPending) return <Loading />;
  if (sentences.isError) return <ErrorState error={sentences.error} />;
  if (sentences.data.length === 0)
    return <Empty title="No sentences yet">Finish a model-sentences lesson.</Empty>;
  return (
    <Card className="p-0 sm:p-0">
      <ul className="divide-y divide-line">
        {sentences.data.map((s) => (
          <li key={s.id} className="flex items-start gap-3 px-5 py-3">
            <SpeakButton text={s.fr} />
            <div>
              <p lang="fr">{fr(s.fr)}</p>
              <p className="text-sm text-muted">{s.en}</p>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function Concepts() {
  const concepts = useLibraryConcepts();
  if (concepts.isPending) return <Loading />;
  if (concepts.isError) return <ErrorState error={concepts.error} />;
  if (concepts.data.length === 0)
    return <Empty title="No grammar yet">Finish a grammar lesson.</Empty>;
  return (
    <div className="space-y-3">
      {concepts.data.map((c) => (
        <details key={c.id} className="group rounded-2xl border border-line bg-surface p-5">
          <summary className="cursor-pointer font-serif text-lg font-semibold" lang="fr">
            {fr(c.title)}
          </summary>
          <div className="mt-4">
            <FrenchMarkdown>{c.body_md}</FrenchMarkdown>
          </div>
        </details>
      ))}
    </div>
  );
}
