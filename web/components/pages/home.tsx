"use client";

import { ArrowRight, Repeat } from "lucide-react";

import { CoverageBar } from "@/components/progress/coverage-bar";
import { ExamPlanCard } from "@/components/progress/exam-plan-card";
import { SkillsPanel } from "@/components/progress/skills-panel";
import { ButtonLink } from "@/components/ui/button";
import { Card, Eyebrow } from "@/components/ui/card";
import { ErrorState, Loading } from "@/components/ui/states";
import { fr } from "@/lib/french";
import { useDueReviews, usePath, useSkills } from "@/lib/queries";

export function HomePage() {
  const path = usePath();
  const due = useDueReviews();
  const skills = useSkills();
  const needsPlacement = skills.data && !skills.data.CO && !skills.data.CE;

  if (path.isPending) return <Loading />;
  if (path.isError) return <ErrorState error={path.error} />;
  const next = path.data.next_lesson;

  return (
    <div className="space-y-6">
      <header>
        <Eyebrow>TCF Canada · objectif NCLC 7</Eyebrow>
        <h1 className="mt-1 font-serif text-3xl font-semibold" lang="fr">
          Bonjour, on continue&#8239;?
        </h1>
      </header>

      {needsPlacement && (
        <Card className="flex flex-col gap-4 bg-accent-soft sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-medium text-accent">Find your starting level</p>
            <p className="text-sm text-muted">
              A 20-minute listening and reading placement sets your skill bars and skips what you
              already know.
            </p>
          </div>
          <ButtonLink href="/placement">Take the placement test</ButtonLink>
        </Card>
      )}

      {next ? (
        <Card className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <Eyebrow>Continue · {fr(next.module_title)}</Eyebrow>
            <p className="mt-1 font-serif text-xl font-semibold" lang="fr">
              {fr(next.lesson_title)}
            </p>
          </div>
          <ButtonLink href={`/lessons/${next.lesson_id}`}>
            Start <ArrowRight className="size-4" aria-hidden />
          </ButtonLink>
        </Card>
      ) : (
        <Card>
          <p className="font-medium">You&apos;re at a module check or the end of the path.</p>
          <ButtonLink href="/path" variant="secondary" className="mt-3">
            Open the path
          </ButtonLink>
        </Card>
      )}

      <div className="grid items-start gap-6 sm:grid-cols-[2fr_1fr]">
        <Card>
          <CoverageBar coverage={path.data.coverage} />
        </Card>
        <Card className="flex flex-col justify-between gap-3">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Repeat className="size-4 text-accent" aria-hidden /> Reviews due
          </div>
          <p className="font-serif text-3xl font-semibold tabular-nums">
            {due.data?.length ?? "–"}
          </p>
          <ButtonLink
            href="/review"
            variant="secondary"
            aria-disabled={!due.data?.length}
            className={due.data?.length ? "" : "pointer-events-none opacity-50"}
          >
            Review
          </ButtonLink>
        </Card>
      </div>

      <ExamPlanCard />

      <SkillsPanel />
    </div>
  );
}
