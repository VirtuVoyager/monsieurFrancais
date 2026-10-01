"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card, Eyebrow, SectionTitle } from "@/components/ui/card";
import { cx } from "@/components/ui/cx";
import { ProgressBar } from "@/components/ui/progress-bar";
import { ErrorState, Loading } from "@/components/ui/states";
import type { Schemas } from "@/lib/api/client";
import { useBudget, useBudgetEvents, useUpdateCaps } from "@/lib/queries";

const SERVICE_LABELS: Record<string, string> = {
  openai: "Azure OpenAI",
  speech: "Azure Speech",
  total: "Total",
};

const usd = (value: string | number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 4,
  }).format(Number(value));

export function BudgetPage() {
  const budget = useBudget();
  const events = useBudgetEvents();

  if (budget.isPending) return <Loading />;
  if (budget.isError) return <ErrorState error={budget.error} />;
  const { services, by_feature, free_allowances, month, price_version } = budget.data;

  return (
    <div className="space-y-6">
      <header>
        <Eyebrow>
          {month} · prices as of {price_version}
        </Eyebrow>
        <h1 className="mt-1 font-serif text-3xl font-semibold">Budget</h1>
        <p className="mt-2 text-sm text-muted">
          Every paid Azure call is checked against these caps before it runs. When a cap is reached,
          lessons, reviews and listening/reading assessments keep working.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-3">
        {Object.entries(services).map(([name, spend]) => (
          <ServiceCard key={name} name={name} spend={spend} />
        ))}
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        <Card className="space-y-3">
          <SectionTitle>Spend by feature</SectionTitle>
          {by_feature.length === 0 ? (
            <p className="text-sm text-muted">No paid calls this month.</p>
          ) : (
            <ul className="divide-y divide-line text-sm">
              {by_feature.map((f) => (
                <li key={f.feature} className="flex justify-between py-2">
                  <span>{f.feature}</span>
                  <span className="tabular-nums">{usd(f.cost_usd)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card className="space-y-4">
          <SectionTitle>Free Speech allowance</SectionTitle>
          {free_allowances.map((a) => (
            <div key={`${a.model}-${a.unit}`}>
              <div className="mb-1 flex justify-between text-sm">
                <span>{a.unit === "characters" ? "Text-to-speech" : "Speech-to-text"}</span>
                <span className="text-muted tabular-nums">
                  {formatUnits(a.used, a.unit)} / {formatUnits(a.allowance, a.unit)}
                </span>
              </div>
              <ProgressBar
                value={(100 * a.used) / a.allowance}
                label={`${a.model} free allowance`}
              />
            </div>
          ))}
        </Card>
      </div>

      <CapsEditor services={services} />

      <Card className="space-y-3">
        <SectionTitle>Recent usage</SectionTitle>
        {events.isPending && <Loading />}
        {events.isError && <ErrorState error={events.error} />}
        {events.data?.length === 0 && <p className="text-sm text-muted">No usage recorded yet.</p>}
        {events.data && events.data.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-muted">
                <tr>
                  <th className="py-2 pr-4 font-medium">When</th>
                  <th className="py-2 pr-4 font-medium">Feature</th>
                  <th className="py-2 pr-4 font-medium">Model</th>
                  <th className="py-2 text-right font-medium">Cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {events.data.map((e, i) => (
                  <tr key={i}>
                    <td className="py-2 pr-4 whitespace-nowrap">
                      {new Date(e.occurred_at).toLocaleString()}
                    </td>
                    <td className="py-2 pr-4">{e.feature}</td>
                    <td className="py-2 pr-4 text-muted">{e.model}</td>
                    <td className="py-2 text-right tabular-nums">{usd(e.cost_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

function ServiceCard({ name, spend }: { name: string; spend: Schemas["ServiceSpend"] }) {
  const cap = Number(spend.cap_usd);
  const used = Number(spend.spent_usd) + Number(spend.reserved_usd);
  const pct = cap > 0 ? (100 * used) / cap : 100;
  return (
    <Card className="space-y-3">
      <Eyebrow>{SERVICE_LABELS[name] ?? name}</Eyebrow>
      <p className="font-serif text-2xl font-semibold tabular-nums">
        {usd(spend.spent_usd)}
        <span className="text-base font-normal text-muted"> / {usd(spend.cap_usd)}</span>
      </p>
      <ProgressBar
        value={pct}
        label={`${name} budget used`}
        className={cx(pct >= 80 && "[&>div]:bg-danger")}
      />
      <p className="text-xs text-muted">Projected month end: {usd(spend.projected_usd)}</p>
    </Card>
  );
}

function CapsEditor({ services }: { services: Record<string, Schemas["ServiceSpend"]> }) {
  const update = useUpdateCaps();
  const [caps, setCaps] = useState(() => ({
    openai: String(services.openai?.cap_usd ?? "0"),
    speech: String(services.speech?.cap_usd ?? "0"),
    total: String(services.total?.cap_usd ?? "0"),
  }));

  const save = (event: FormEvent) => {
    event.preventDefault();
    update.mutate(caps);
  };

  return (
    <Card>
      <form onSubmit={save} className="space-y-4">
        <SectionTitle>Monthly caps (USD)</SectionTitle>
        <p className="text-sm text-muted">
          Each paid call must fit both its service cap and the total. The total is an overall
          ceiling, not the sum: set it below OpenAI + Speech to let whichever service you use more
          take the room, while the bill never passes the total.
        </p>
        <div className="grid gap-4 sm:grid-cols-3">
          {(Object.keys(caps) as (keyof typeof caps)[]).map((service) => (
            <label key={service} className="block text-sm">
              <span className="mb-1 block font-medium">{SERVICE_LABELS[service]}</span>
              <input
                type="number"
                min={0}
                step="0.5"
                value={caps[service]}
                onChange={(e) => setCaps({ ...caps, [service]: e.target.value })}
                className="w-full rounded-xl border border-line bg-surface px-3 py-2 tabular-nums outline-none focus:border-accent"
              />
            </label>
          ))}
        </div>
        {Number(caps.total) > Number(caps.openai) + Number(caps.speech) && (
          <p className="text-sm text-danger">
            The total is above OpenAI + Speech, so it can never be reached; the service caps decide.
          </p>
        )}
        <div className="flex items-center gap-3">
          <Button type="submit" disabled={update.isPending}>
            Save caps
          </Button>
          {update.isSuccess && <span className="text-sm text-success">Saved</span>}
          {update.isError && <span className="text-sm text-danger">{update.error.message}</span>}
        </div>
      </form>
    </Card>
  );
}

function formatUnits(value: number, unit: string): string {
  if (unit === "audio_seconds") return `${(value / 3600).toFixed(1)} h`;
  if (unit === "characters") return `${Math.round(value / 1000)}k chars`;
  return String(value);
}
