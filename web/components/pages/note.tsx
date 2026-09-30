"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button, ButtonLink } from "@/components/ui/button";
import { Card, Eyebrow, SectionTitle } from "@/components/ui/card";
import { FrenchMarkdown } from "@/components/ui/markdown";
import { ErrorState, Loading } from "@/components/ui/states";
import type { Schemas } from "@/lib/api/client";
import { useNote, useReviewNote } from "@/lib/queries";

type Item = Schemas["NoteItemOut"];
type Draft = { approve: boolean; fr: string; en: string; gender: "m" | "f" | "" };

const SECTIONS = [
  { kind: "word", title: "Words" },
  { kind: "sentence", title: "Phrases" },
  { kind: "grammar", title: "Grammar" },
] as const;

const field =
  "w-full rounded-lg border border-line bg-surface px-2.5 py-1.5 text-sm outline-none focus:border-accent";

export function NotePage({ id }: { id: number }) {
  const note = useNote(id);
  if (note.isPending) return <Loading />;
  if (note.isError) return <ErrorState error={note.error} />;
  return <NoteReview key={note.data.id} note={note.data} />;
}

function NoteReview({ note }: { note: Schemas["NoteDetail"] }) {
  const save = useReviewNote(note.id);
  // Proposed items start ticked: approving is the common case, skipping the exception.
  const [drafts, setDrafts] = useState<Record<number, Draft>>(() =>
    Object.fromEntries(
      note.items.map((i) => [
        i.id,
        {
          approve: i.status !== "rejected",
          fr: i.fr,
          en: i.en,
          gender: i.gender === "m" || i.gender === "f" ? i.gender : "",
        },
      ]),
    ),
  );
  const edit = (id: number, change: Partial<Draft>) =>
    setDrafts((all) => ({ ...all, [id]: { ...all[id]!, ...change } }));
  const approved = Object.values(drafts).filter((d) => d.approve).length;

  const submit = () =>
    save.mutate(
      note.items.map((i) => {
        const d = drafts[i.id]!;
        return { id: i.id, approve: d.approve, fr: d.fr, en: d.en, gender: d.gender };
      }),
    );

  return (
    <div className="space-y-6 pb-24">
      <header className="space-y-2">
        <Link href="/notes" className="inline-flex items-center gap-1 text-sm text-muted">
          <ArrowLeft className="size-4" aria-hidden /> Class notes
        </Link>
        <Eyebrow>{note.day !== null ? `Day ${note.day}` : note.filename}</Eyebrow>
        <h1 className="font-serif text-2xl font-semibold">{note.title}</h1>
      </header>

      {note.status === "pending" && (
        <Card>
          This note is saved but hasn&apos;t been read yet: the model or your budget was
          unavailable. It is retried every 10 minutes.
        </Card>
      )}
      {note.status === "ready" && note.items.length === 0 && (
        <Card>Nothing new in this note: everything in it is already in your Library.</Card>
      )}

      {SECTIONS.map(({ kind, title }) => {
        const items = note.items.filter((i) => i.kind === kind);
        if (items.length === 0) return null;
        return (
          <section key={kind} className="space-y-3">
            <div className="flex items-center justify-between">
              <SectionTitle>
                {title} <span className="text-muted">({items.length})</span>
              </SectionTitle>
              <div className="flex gap-2 text-sm">
                {[true, false].map((approve) => (
                  <button
                    key={String(approve)}
                    type="button"
                    className="text-muted hover:text-ink"
                    onClick={() => items.forEach((i) => edit(i.id, { approve }))}
                  >
                    {approve ? "All" : "None"}
                  </button>
                ))}
              </div>
            </div>
            <Card className="divide-y divide-line p-0 sm:p-0">
              {items.map((item) => (
                <Row key={item.id} item={item} draft={drafts[item.id]!} edit={edit} />
              ))}
            </Card>
          </section>
        );
      })}

      <details className="rounded-2xl border border-line bg-surface p-5">
        <summary className="cursor-pointer font-medium">Original note</summary>
        <div className="mt-4">
          <FrenchMarkdown>{note.body_md}</FrenchMarkdown>
        </div>
      </details>

      {note.items.length > 0 && (
        <div className="fixed inset-x-0 bottom-16 z-10 border-t border-line bg-surface/95 px-4 py-3 backdrop-blur md:bottom-0 md:left-60">
          <div className="mx-auto flex max-w-4xl items-center justify-between gap-4">
            <p className="text-sm text-muted" aria-live="polite">
              {save.isSuccess
                ? "Saved. Approved words and phrases are now in Review."
                : save.isError
                  ? save.error.message
                  : `${approved} of ${note.items.length} selected`}
            </p>
            <div className="flex gap-2">
              {save.isSuccess && (
                <ButtonLink href="/review" variant="secondary">
                  Review now
                </ButtonLink>
              )}
              <Button onClick={submit} disabled={save.isPending}>
                Save
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Row({
  item,
  draft,
  edit,
}: {
  item: Item;
  draft: Draft;
  edit: (id: number, change: Partial<Draft>) => void;
}) {
  const label = `Keep ${item.fr}`;
  return (
    <div className={draft.approve ? "px-5 py-3" : "px-5 py-3 opacity-50"}>
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={draft.approve}
          onChange={(e) => edit(item.id, { approve: e.target.checked })}
          aria-label={label}
          className="mt-2.5 size-4 accent-[var(--color-accent)]"
        />
        <div className="grid flex-1 gap-2 sm:grid-cols-[1fr_1fr_auto]">
          <input
            lang={item.kind === "grammar" ? "en" : "fr"}
            value={draft.fr}
            onChange={(e) => edit(item.id, { fr: e.target.value })}
            aria-label={item.kind === "grammar" ? "Title" : "French"}
            className={field}
          />
          {item.kind !== "grammar" && (
            <input
              value={draft.en}
              onChange={(e) => edit(item.id, { en: e.target.value })}
              aria-label="English"
              className={field}
            />
          )}
          {item.kind === "word" && (
            <select
              value={draft.gender}
              onChange={(e) => edit(item.id, { gender: e.target.value as Draft["gender"] })}
              aria-label="Gender"
              className={field}
            >
              <option value="">—</option>
              <option value="m">masc.</option>
              <option value="f">fém.</option>
            </select>
          )}
        </div>
      </div>
      {item.kind === "word" && item.detail && (
        <p lang="fr" className="mt-1 ml-7 text-sm text-muted">
          {item.detail}
        </p>
      )}
      {item.kind === "grammar" && (
        <details className="mt-2 ml-7">
          <summary className="cursor-pointer text-sm text-muted">Explanation</summary>
          <div className="mt-2 text-sm">
            <FrenchMarkdown>{item.detail}</FrenchMarkdown>
          </div>
        </details>
      )}
    </div>
  );
}
