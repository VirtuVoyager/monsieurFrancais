"use client";

import { CoverageBar } from "@/components/progress/coverage-bar";
import { SkillsPanel } from "@/components/progress/skills-panel";
import { Card, SectionTitle } from "@/components/ui/card";
import { ProgressBar } from "@/components/ui/progress-bar";
import { ErrorState, Loading } from "@/components/ui/states";
import { usePath } from "@/lib/queries";

export function ProgressPage() {
  const path = usePath();
  if (path.isPending) return <Loading />;
  if (path.isError) return <ErrorState error={path.error} />;

  return (
    <div className="space-y-6">
      <h1 className="font-serif text-3xl font-semibold">Progress</h1>
      <Card className="space-y-5">
        <SectionTitle>Curriculum</SectionTitle>
        <CoverageBar coverage={path.data.coverage} />
        <div className="grid gap-4 sm:grid-cols-2">
          {path.data.levels.map((level) => (
            <div key={level.id}>
              <div className="mb-1 flex justify-between text-sm">
                <span className="font-medium">{level.id}</span>
                <span className="text-muted tabular-nums">
                  {level.covered}/{level.total}
                </span>
              </div>
              <ProgressBar
                value={level.total ? (100 * level.covered) / level.total : 0}
                label={`${level.id} coverage`}
              />
            </div>
          ))}
        </div>
      </Card>
      <SkillsPanel />
    </div>
  );
}
