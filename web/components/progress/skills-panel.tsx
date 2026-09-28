import { axisPosition, SKILLS } from "@/lib/scales";

import { Card, SectionTitle } from "../ui/card";
import { SkillBar } from "./skill-bar";

/** Skill bars fill in once timed assessments exist; until then they show the target only. */
export function SkillsPanel() {
  return (
    <Card className="space-y-5">
      <div>
        <SectionTitle>Skills under exam conditions</SectionTitle>
        <p className="text-muted mt-1 text-sm">
          Only timed checkpoints, level exams, mocks and drills move these bars. The line marks NCLC
          7.
        </p>
      </div>
      {SKILLS.map((skill) => (
        <SkillBar
          key={skill.code}
          skill={skill.name}
          estimate={null}
          targetPosition={axisPosition(skill.nclc7, skill.receptive)}
        />
      ))}
    </Card>
  );
}
