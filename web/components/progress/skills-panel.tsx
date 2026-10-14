"use client";

import type { Schemas } from "@/lib/api/client";
import { useSkills } from "@/lib/queries";
import { axisPosition, SKILLS } from "@/lib/scales";

import { ButtonLink } from "../ui/button";
import { Card, SectionTitle } from "../ui/card";
import { SkillBar, type SkillEstimateView } from "./skill-bar";

export function SkillsPanel() {
  const skills = useSkills();
  const levels = skills.data ?? {};
  const rows = SKILLS.map((skill) => {
    const level = levels[skill.code];
    return { skill, view: level ? estimateView(level, skill.receptive) : null };
  });
  const weakest = rows
    .flatMap(({ skill, view }) => (view ? [{ skill, position: view.position }] : []))
    .sort((a, b) => a.position - b.position)[0]?.skill;

  return (
    <Card className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <SectionTitle>Skills under exam conditions</SectionTitle>
          <p className="mt-1 text-sm text-muted">
            Only timed drills, checkpoints, level exams and mocks move these bars. The line marks
            NCLC 7.
            {weakest && (
              <>
                {" "}
                Your weakest skill is <strong className="text-ink">{weakest.name}</strong>.
              </>
            )}
          </p>
        </div>
        <ButtonLink href="/drills" variant="secondary">
          Timed drill
        </ButtonLink>
      </div>
      {rows.map(({ skill, view }) => (
        <SkillBar
          key={skill.code}
          skill={skill.name}
          estimate={view}
          targetPosition={axisPosition(skill.nclc7, skill.receptive)}
          highlight={weakest?.code === skill.code}
        />
      ))}
    </Card>
  );
}

function estimateView(level: Schemas["SkillLevelOut"], receptive: boolean): SkillEstimateView {
  const position = axisPosition(level.score, receptive);
  const high = axisPosition(level.score + level.se, receptive);
  const scale = receptive ? "/699" : "/20";
  return {
    label: `${level.cefr}, NCLC ${level.nclc ?? "below 4"}`,
    position,
    spread: Math.max(high - position, 1),
    caption: `est. ${Math.round(level.score)}${scale} (±${Math.round(level.se)}) · ${level.cefr} · NCLC ${level.nclc ?? "<4"}`,
    stale: level.stale,
  };
}
