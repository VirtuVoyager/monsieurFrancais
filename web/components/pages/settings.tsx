"use client";

import { useState, type FormEvent } from "react";

import { ExamPlanCard } from "@/components/progress/exam-plan-card";
import { Button, ButtonLink } from "@/components/ui/button";
import { Card, SectionTitle } from "@/components/ui/card";
import { ErrorState, Loading } from "@/components/ui/states";
import type { Schemas } from "@/lib/api/client";
import { useChangePassphrase, useSettings, useSignOut, useUpdateSettings } from "@/lib/queries";

const input =
  "mt-1 w-full rounded-xl border border-line bg-surface px-3 py-2 outline-none focus:border-accent";

export function SettingsPage() {
  const settings = useSettings();
  if (settings.isPending) return <Loading />;
  if (settings.isError) return <ErrorState error={settings.error} />;
  return (
    <div className="space-y-6">
      <h1 className="font-serif text-3xl font-semibold">Settings</h1>
      <ExamPlanCard />
      <SettingsForm initial={settings.data.settings} />
      <Card className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted">
          Azure spend, monthly caps and the free Speech allowance.
        </p>
        <ButtonLink href="/settings/budget" variant="secondary">
          Budget
        </ButtonLink>
      </Card>
      <SecurityCard />
    </div>
  );
}

function SecurityCard() {
  const change = useChangePassphrase();
  const signOut = useSignOut();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const mismatch = repeat !== "" && repeat !== next;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    change.mutate(
      { current, new: next },
      {
        onSuccess: () => {
          setCurrent("");
          setNext("");
          setRepeat("");
        },
      },
    );
  };

  return (
    <Card className="space-y-5">
      <SectionTitle>Sign-in and security</SectionTitle>
      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-3">
          <label className="block text-sm font-medium">
            Current passphrase
            <input
              type="password"
              autoComplete="current-password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              className={input}
            />
          </label>
          <label className="block text-sm font-medium">
            New passphrase
            <input
              type="password"
              autoComplete="new-password"
              minLength={8}
              value={next}
              onChange={(e) => setNext(e.target.value)}
              className={input}
            />
          </label>
          <label className="block text-sm font-medium">
            New passphrase again
            <input
              type="password"
              autoComplete="new-password"
              value={repeat}
              onChange={(e) => setRepeat(e.target.value)}
              className={input}
            />
          </label>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="submit"
            disabled={!current || next.length < 8 || next !== repeat || change.isPending}
          >
            Change passphrase
          </Button>
          {mismatch && <span className="text-sm text-danger">The new passphrases differ</span>}
          {change.isSuccess && (
            <span role="status" className="text-sm text-success">
              Changed. Your other devices are signed out.
            </span>
          )}
          {change.isError && (
            <span role="alert" className="text-sm text-danger">
              {change.error.message}
            </span>
          )}
        </div>
      </form>
      <div className="flex flex-wrap items-center gap-3 border-t border-line pt-4">
        <Button variant="secondary" onClick={() => signOut.mutate(false)}>
          Sign out
        </Button>
        <Button variant="secondary" onClick={() => signOut.mutate(true)}>
          Sign out everywhere
        </Button>
        <p className="text-sm text-muted">
          Everywhere ends every session on every device, including this one.
        </p>
      </div>
    </Card>
  );
}

function SettingsForm({ initial }: { initial: Schemas["LearnerSettings"] }) {
  const update = useUpdateSettings();
  const [form, setForm] = useState(initial);
  const set = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) =>
    setForm({ ...form, [key]: value });

  const save = (event: FormEvent) => {
    event.preventDefault();
    update.mutate(form);
  };

  return (
    <Card>
      <form onSubmit={save} className="space-y-5">
        <SectionTitle>Your exam</SectionTitle>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm font-medium">
            Exam date
            <input
              type="date"
              value={form.exam_date ?? ""}
              onChange={(e) => set("exam_date", e.target.value || null)}
              className={input}
            />
          </label>
          <label className="block text-sm font-medium">
            Target NCLC (every skill)
            <select
              value={form.target_nclc}
              onChange={(e) => set("target_nclc", Number(e.target.value))}
              className={input}
            >
              {[5, 6, 7, 8, 9, 10].map((n) => (
                <option key={n} value={n}>
                  NCLC {n}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm font-medium">
            Study minutes per day
            <input
              type="number"
              min={15}
              max={600}
              step={15}
              value={form.daily_minutes}
              onChange={(e) => set("daily_minutes", Number(e.target.value))}
              className={input}
            />
          </label>
          <label className="block text-sm font-medium sm:col-span-2">
            Timezone
            <input
              value={form.timezone}
              onChange={(e) => set("timezone", e.target.value)}
              className={input}
            />
          </label>
        </div>
        <div className="flex items-center gap-3">
          <Button type="submit" disabled={update.isPending}>
            Save
          </Button>
          {update.isSuccess && <span className="text-sm text-success">Saved</span>}
          {update.isError && <span className="text-sm text-danger">{update.error.message}</span>}
        </div>
      </form>
    </Card>
  );
}
