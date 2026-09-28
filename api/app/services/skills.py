from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.scales import (
    CEFR_DIFFICULTY,
    PRODUCTIVE,
    RECEPTIVE,
    ExamScales,
    load_exam_scales,
    tcf_from_theta,
)
from app.domain.skill_estimate import SOURCE_WEIGHTS, Estimate, ItemEvidence, receptive
from app.models import AssessmentRun, Item, Response
from app.services.path import load_path


@dataclass(frozen=True)
class SkillLevel:
    skill: str
    estimate: Estimate
    cefr: str
    nclc: int | None


@lru_cache
def exam_scales() -> ExamScales:
    return load_exam_scales(get_settings().content_dir / "exam_scales.yaml")


def receptive_evidence(session: Session, user_id: int, skill: str) -> list[ItemEvidence]:
    rows = session.execute(
        select(Item.difficulty, Response.correct, AssessmentRun.kind, AssessmentRun.finished_at)
        .join(Response, Response.item_id == Item.id)
        .join(AssessmentRun, AssessmentRun.id == Response.run_id)
        .where(
            AssessmentRun.user_id == user_id,
            AssessmentRun.kind.in_(SOURCE_WEIGHTS),
            AssessmentRun.finished_at.is_not(None),
            Response.skill == skill,
        )
    )
    return [
        ItemEvidence(difficulty, bool(correct), kind, finished_at)
        for difficulty, correct, kind, finished_at in rows
        if finished_at is not None
    ]


def skill_level(session: Session, user_id: int, skill: str) -> SkillLevel | None:
    # Writing and speaking estimates arrive with the rubric grader.
    if skill in PRODUCTIVE:
        return None
    estimate = receptive(receptive_evidence(session, user_id, skill), datetime.now(UTC))
    if estimate is None:
        return None
    scales = exam_scales()
    return SkillLevel(
        skill, estimate, scales.cefr(skill, estimate.score), scales.nclc(skill, estimate.score)
    )


def all_levels(session: Session, user_id: int) -> dict[str, SkillLevel | None]:
    return {skill: skill_level(session, user_id, skill) for skill in (*RECEPTIVE, *PRODUCTIVE)}


def working_ability(session: Session, user_id: int, skill: str) -> float:
    """Current ability in logits: the estimate if one exists, else the learner's path level."""
    level = skill_level(session, user_id, skill)
    if level is not None:
        return (level.estimate.score - tcf_from_theta(0)) / 100
    view = load_path(session, user_id)
    current = next(
        (m.level_id for m in view.modules if view.status[m.id] == "open"),
        view.modules[-1].level_id if view.modules else "A1",
    )
    return CEFR_DIFFICULTY[current]
