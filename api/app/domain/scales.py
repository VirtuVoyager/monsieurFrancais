from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
RECEPTIVE = ("CO", "CE")
PRODUCTIVE = ("EE", "EO")

# Rasch difficulty prior (logits) for an item authored at each CEFR level. With
# tcf_from_theta below, a learner in the middle of a level gets 50% on that level's items.
CEFR_DIFFICULTY = {"A1": -2.5, "A2": -1.5, "B1": -0.5, "B2": 0.5, "C1": 1.5, "C2": 2.5}


def tcf_from_theta(theta: float) -> float:
    return min(max(400.0 + 100.0 * theta, 100.0), 699.0)


@dataclass(frozen=True)
class WritingSpec:
    min_words: int
    max_words: int
    minutes: int


@dataclass(frozen=True)
class SpeakingSpec:
    prep_seconds: int
    seconds: int


@dataclass(frozen=True)
class ExamScales:
    cefr_bands: dict[str, dict[str, tuple[float, float]]]
    nclc_floors: dict[str, dict[int, float]]
    seconds_per_item: dict[str, int]
    writing_tasks: dict[str, WritingSpec]
    speaking_tasks: dict[str, SpeakingSpec]

    def cefr(self, skill: str, score: float) -> str:
        bands = self.cefr_bands["receptive" if skill in RECEPTIVE else "productive"]
        level = CEFR_LEVELS[0]
        for name, (low, _) in bands.items():
            if score >= low:
                level = name
        return level

    def nclc(self, skill: str, score: float) -> int | None:
        reached = [level for level, floor in self.nclc_floors[skill].items() if score >= floor]
        return max(reached) if reached else None


def load_exam_scales(path: Path) -> ExamScales:
    raw: dict[str, Any] = yaml.safe_load(path.read_text())
    return ExamScales(
        cefr_bands={
            kind: {level: (float(lo), float(hi)) for level, (lo, hi) in bands.items()}
            for kind, bands in raw["cefr_bands"].items()
        },
        nclc_floors={
            skill: {int(level): float(floor) for level, floor in floors.items()}
            for skill, floors in raw["nclc"].items()
        },
        seconds_per_item={skill: int(v) for skill, v in raw["seconds_per_item"].items()},
        writing_tasks={task: WritingSpec(**spec) for task, spec in raw["writing_tasks"].items()},
        speaking_tasks={task: SpeakingSpec(**spec) for task, spec in raw["speaking_tasks"].items()},
    )
