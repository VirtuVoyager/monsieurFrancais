"use client";

import { NotebookPen, Search } from "lucide-react";
import { useDeferredValue, useState } from "react";

import Link from "next/link";

import { GenderTag } from "@/components/lesson/gender-tag";
import { SpeakButton } from "@/components/lesson/speak-button";
import { Badge } from "@/components/ui/badge";
import { ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cx } from "@/components/ui/cx";
import { FrenchMarkdown } from "@/components/ui/markdown";
import { Empty, ErrorState, Loading } from "@/components/ui/states";
import { fr } from "@/lib/french";
import { useLibraryConcepts, useLibrarySentences, useLibraryWords, useSearch } from "@/lib/queries";

const TABS = ["Words", "Sentences", "Grammar"] as const;
type Tab = (typeof TABS)[number];

const KIND_LABELS: Record<string, string> = {
  word: "Word",
  sentence: "Sentence",
  grammar: "Grammar",
  error: "Your error",
  feedback: "Your feedback",
};

export function LibraryPage() {
  const [tab, setTab] = useState<Tab>("Words");
  const [query, setQuery] = useState("");
  const [everything, setEverything] = useState(false);
  const q = useDeferredValue(query.trim());

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="font-serif text-3xl font-semibold">Library</h1>
        <ButtonLink href="/notes" variant="secondary">
          <NotebookPen className="size-4" aria-hidden />
          Class notes
        </ButtonLink>
      </div>
      <div className="space-y-2">
        <label className="relative block">
          <span className="sr-only">Search</span>
          <Search className="absolute top-3 left-3 size-4 text-muted" aria-hidden />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search words, sentences, grammar and your own mistakes"
            className="w-full rounded-xl border border-line bg-surface py-2.5 pr-3 pl-9 outline-none focus:border-accent"
          />
        </label>
        <label className="flex items-center gap-2 text-sm text-muted">
          <input
            type="checkbox"
            checked={everything}
            onChange={(e) => setEverything(e.target.checked)}
          />
          Include modules I haven&apos;t started
        </label>
      </div>
      {q.length > 1 ? (
        <SearchResults q={q} scope={everything ? "catalogue" : "learned"} />
      ) : (
        <>
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
          {tab === "Words" && <Words />}
          {tab === "Sentences" && <Sentences />}
          {tab === "Grammar" && <Concepts />}
        </>
      )}
    </div>
  );
}

function SearchResults({ q, scope }: { q: string; scope: "learned" | "catalogue" }) {
  const results = useSearch(q, scope);
  if (results.isPending) return <Loading />;
  if (results.isError) return <ErrorState error={results.error} />;
  if (results.data.length === 0) return <Empty title="Nothing found" />;
  return (
    <Card className="p-0 sm:p-0">
      <ul className="divide-y divide-line">
        {results.data.map((hit) => (
          <li key={hit.key}>
            <Link href={hit.source_ref} className="block px-5 py-3 hover:bg-surface-2">
              <div className="flex items-center gap-2">
                <Badge tone={hit.personal ? "danger" : "accent"}>
                  {KIND_LABELS[hit.kind] ?? hit.kind}
                </Badge>
                {hit.cefr && <span className="text-xs text-muted">{hit.cefr}</span>}
              </div>
              <p lang="fr" className="mt-1 font-medium">
                {fr(hit.title)}
              </p>
              <p className="line-clamp-2 text-sm text-muted">{fr(hit.text)}</p>
            </Link>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function Words() {
  const words = useLibraryWords("");
  if (words.isPending) return <Loading />;
  if (words.isError) return <ErrorState error={words.error} />;
  if (words.data.length === 0)
    return (
      <Empty title="No words yet">
        Finish a vocabulary lesson or approve words from your class notes.
      </Empty>
    );
  return (
    <Card className="p-0 sm:p-0">
      <ul className="divide-y divide-line">
        {words.data.map((w) => (
          <li key={w.id} className="flex items-center gap-3 px-5 py-3">
            <SpeakButton text={w.lemma} url={w.audio_url} />
            <span lang="fr" className="font-medium">
              {fr(w.lemma)}
            </span>
            <GenderTag gender={w.gender} />
            <Source source={w.source} />
            <span className="ml-auto text-sm text-muted">{w.en}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function Sentences() {
  const sentences = useLibrarySentences("");
  if (sentences.isPending) return <Loading />;
  if (sentences.isError) return <ErrorState error={sentences.error} />;
  if (sentences.data.length === 0)
    return (
      <Empty title="No sentences yet">
        Finish a model-sentences lesson or approve phrases from your class notes.
      </Empty>
    );
  return (
    <Card className="p-0 sm:p-0">
      <ul className="divide-y divide-line">
        {sentences.data.map((s) => (
          <li key={s.id} className="flex items-start gap-3 px-5 py-3">
            <SpeakButton text={s.fr} url={s.audio_url} />
            <div>
              <p lang="fr">{fr(s.fr)}</p>
              <p className="text-sm text-muted">
                {s.en} <Source source={s.source} />
              </p>
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
    return (
      <Empty title="No grammar yet">
        Finish a grammar lesson or approve grammar from your class notes.
      </Empty>
    );
  return (
    <div className="space-y-3">
      {concepts.data.map((c) => (
        <details key={c.id} className="group rounded-2xl border border-line bg-surface p-5">
          <summary className="cursor-pointer font-serif text-lg font-semibold" lang="fr">
            {fr(c.title)} <Source source={c.source} />
          </summary>
          <div className="mt-4">
            <FrenchMarkdown>{c.body_md}</FrenchMarkdown>
          </div>
        </details>
      ))}
    </div>
  );
}

function Source({ source }: { source: string | null | undefined }) {
  if (!source) return null;
  return (
    <span className="rounded-full bg-accent-soft px-2 py-0.5 font-sans text-[11px] font-medium text-accent">
      {source}
    </span>
  );
}
