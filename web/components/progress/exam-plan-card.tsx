"use client";

import { AlertTriangle, CalendarDays } from "lucide-react";

import { useSettings } from "@/lib/queries";

import { ButtonLink } from "../ui/button";
import { Card, Eyebrow } from "../ui/card";

const formatDate = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

export function ExamPlanCard() {
  const settings = useSettings();
  if (!settings.data) return null;
  const { plan } = settings.data;

  if (!plan) {
    return (
      <Card className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm">
          Set your exam date to get a booking deadline, a retake window and the right mock schedule.
        </p>
        <ButtonLink href="/settings" variant="secondary">
          Set exam date
        </ButtonLink>
      </Card>
    );
  }

  return (
    <Card className="grid gap-4 sm:grid-cols-4">
      <div className="sm:col-span-1">
        <Eyebrow>TCF Canada</Eyebrow>
        <p className="mt-1 flex items-center gap-2 font-serif text-2xl font-semibold tabular-nums">
          <CalendarDays className="size-5 text-accent" aria-hidden />
          {plan.days_left} days
        </p>
        <p className="text-xs text-muted">{formatDate(plan.exam_date)}</p>
      </div>
      <Fact label="Book the test by" value={formatDate(plan.book_by)} warn={plan.booking_overdue} />
      <Fact label="Earliest retake" value={formatDate(plan.earliest_retake)} />
      <Fact
        label="Full mocks"
        value={plan.final_phase ? "Weekly (final 4 weeks)" : "Monthly from B1"}
      />
    </Card>
  );
}

function Fact({ label, value, warn = false }: { label: string; value: string; warn?: boolean }) {
  return (
    <div>
      <Eyebrow>{label}</Eyebrow>
      <p className={`mt-1 flex items-center gap-1 font-medium ${warn ? "text-danger" : ""}`}>
        {warn && <AlertTriangle className="size-4" aria-label="Booking deadline passed" />}
        {value}
      </p>
    </div>
  );
}
