"use client";

import { useState, type FormEvent } from "react";

import { ExamPlanCard } from "@/components/progress/exam-plan-card";
import { Button, ButtonLink } from "@/components/ui/button";
import { Card, SectionTitle } from "@/components/ui/card";
import { ErrorState, Loading } from "@/components/ui/states";
import type { Schemas } from "@/lib/api/client";
import { useSettings, useUpdateSettings } from "@/lib/queries";

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
    </div>
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
          <label className="block text-sm font-medium">
            Listening accents
            <select
              value={form.accent_mix}
              onChange={(e) => set("accent_mix", e.target.value as typeof form.accent_mix)}
              className={input}
            >
              <option value="mixed">France and Québec</option>
              <option value="france">Mostly France</option>
              <option value="quebec">Mostly Québec</option>
            </select>
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
