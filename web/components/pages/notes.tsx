"use client";

import { FileUp, NotebookPen } from "lucide-react";
import Link from "next/link";
import { useState, type DragEvent } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, Eyebrow } from "@/components/ui/card";
import { cx } from "@/components/ui/cx";
import { Empty, ErrorState, Loading } from "@/components/ui/states";
import type { Schemas } from "@/lib/api/client";
import { useNotes, useUploadNote } from "@/lib/queries";

const MAX_CHARS = 100_000;

type Upload = { name: string; state: "uploading" | "done" | "failed"; detail: string };

export function NotesPage() {
  const notes = useNotes();
  return (
    <div className="space-y-6">
      <header>
        <Eyebrow>From your classes</Eyebrow>
        <h1 className="mt-1 font-serif text-3xl font-semibold">Class notes</h1>
        <p className="mt-2 text-muted">
          Upload each day&apos;s notes. The words, phrases and grammar in them are proposed for your
          approval, then join your Library, Review and search.
        </p>
      </header>
      <Uploader />
      {notes.isPending && <Loading />}
      {notes.isError && <ErrorState error={notes.error} />}
      {notes.data?.length === 0 && (
        <Empty title="No notes yet">Your uploaded notes will appear here, newest day first.</Empty>
      )}
      {notes.data && notes.data.length > 0 && (
        <div className="space-y-3">
          {notes.data.map((note) => (
            <NoteRow key={note.id} note={note} />
          ))}
        </div>
      )}
    </div>
  );
}

function Uploader() {
  const upload = useUploadNote();
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [dragging, setDragging] = useState(false);

  const report = (name: string, state: Upload["state"], detail: string) =>
    setUploads((all) => [...all.filter((u) => u.name !== name), { name, state, detail }]);

  // One file at a time: each note is extracted as it arrives, and a failure stays visible.
  const send = async (files: File[]) => {
    for (const file of files) {
      const text = await file.text();
      if (text.length > MAX_CHARS) {
        report(file.name, "failed", "Too long: split it into smaller notes.");
        continue;
      }
      report(file.name, "uploading", "Reading your note…");
      try {
        const note = await upload.mutateAsync({ filename: file.name, text });
        report(
          file.name,
          "done",
          note.status === "ready"
            ? `${note.proposed} items to review`
            : "Saved; extraction will retry shortly",
        );
      } catch (e) {
        report(file.name, "failed", e instanceof Error ? e.message : "Upload failed");
      }
    }
  };

  const onDrop = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setDragging(false);
    void send(Array.from(e.dataTransfer.files));
  };

  return (
    <div className="space-y-3">
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cx(
          "flex cursor-pointer flex-col items-center gap-2 rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-colors",
          dragging ? "border-accent bg-accent-soft" : "border-line bg-surface hover:bg-surface-2",
        )}
      >
        <FileUp className="size-7 text-accent" aria-hidden />
        <span className="font-medium">Drop Markdown notes here, or choose files</span>
        <span className="text-sm text-muted">.md or .txt, one file per note</span>
        <input
          type="file"
          multiple
          accept=".md,.markdown,.txt,text/markdown,text/plain"
          className="sr-only"
          aria-label="Upload notes"
          onChange={(e) => {
            void send(Array.from(e.target.files ?? []));
            e.target.value = "";
          }}
        />
      </label>
      {uploads.length > 0 && (
        <ul className="space-y-1 text-sm" aria-live="polite">
          {uploads.map((u) => (
            <li key={u.name} className="flex gap-2">
              <span className="font-medium">{u.name}</span>
              <span className={u.state === "failed" ? "text-danger" : "text-muted"}>
                {u.detail}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function NoteRow({ note }: { note: Schemas["NoteSummary"] }) {
  return (
    <Link href={`/notes/${note.id}`} className="block">
      <Card className="flex items-center gap-4 transition-colors hover:bg-surface-2">
        <NotebookPen className="size-5 shrink-0 text-accent" aria-hidden />
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium">{note.title}</p>
          <p className="text-sm text-muted">
            {note.status === "pending"
              ? "Waiting to be read: the model or budget was unavailable"
              : `${note.approved} approved · ${note.rejected} skipped`}
          </p>
        </div>
        {note.day !== null && <Badge>Day {note.day}</Badge>}
        {note.proposed > 0 && <Badge tone="accent">{note.proposed} to review</Badge>}
      </Card>
    </Link>
  );
}
