import random
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.coverage import Status
from app.domain.scales import CEFR_LEVELS, RECEPTIVE
from app.models import AssessmentRun, Item, Module
from app.schemas.learning import ItemAnswer
from app.services import drills
from app.services.path import module_progress
from app.services.skills import SkillLevel, skill_level

KIND = "placement"
PER_LEVEL = 2


@dataclass(frozen=True)
class Placement:
    grade: drills.RunGrade
    levels: dict[str, SkillLevel | None]
    placed_level: str
    modules_placed: int


def start(session: Session, user_id: int) -> tuple[AssessmentRun, list[Item]]:
    """Both reading and listening, spread across every level so the estimate isn't capped."""
    chosen: list[Item] = []
    for skill in RECEPTIVE:
        by_level: dict[str, list[Item]] = {}
        for item in drills.bank(session, skill):
            by_level.setdefault(item.cefr, []).append(item)
        section = [
            item
            for level in CEFR_LEVELS
            for item in random.sample(
                by_level.get(level, []), min(PER_LEVEL, len(by_level.get(level, [])))
            )
        ]
        chosen += sorted(section, key=lambda item: item.difficulty)
    return drills.create_run(session, user_id, KIND, "+".join(RECEPTIVE), chosen), chosen


def submit(session: Session, user_id: int, run_id: int, answers: list[ItemAnswer]) -> Placement:
    grade = drills.submit(session, user_id, run_id, answers, kind=KIND)
    levels = {skill: skill_level(session, user_id, skill) for skill in RECEPTIVE}
    # Like IRCC, the weaker skill decides where the learner starts.
    placed_level = min(
        (level.cefr for level in levels.values() if level is not None),
        key=CEFR_LEVELS.index,
        default=CEFR_LEVELS[0],
    )
    below = CEFR_LEVELS[: CEFR_LEVELS.index(placed_level)]
    placed = 0
    for module in session.scalars(select(Module).order_by(Module.order)):
        if module.level_id not in below:
            continue
        progress = module_progress(session, user_id, module.id)
        if progress.covered_at is None and progress.status != Status.PLACED:
            progress.status = Status.PLACED
            placed += 1
    session.commit()
    return Placement(grade, levels, placed_level, placed)
