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
from app.domain.skill_estimate import (
    SOURCE_WEIGHTS,
    Estimate,
    ItemEvidence,
    RubricEvidence,
    productive,
    receptive,
)
from app.models import AssessmentRun, Item, Response, WritingSubmission
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


def writing_evidence(session: Session, user_id: int) -> list[RubricEvidence]:
    rows = session.execute(
        select(WritingSubmission.score, AssessmentRun.kind, WritingSubmission.graded_at)
        .join(AssessmentRun, AssessmentRun.id == WritingSubmission.run_id)
        .where(
            WritingSubmission.user_id == user_id,
            WritingSubmission.skill == "EE",
            WritingSubmission.status == "graded",
            AssessmentRun.kind.in_(SOURCE_WEIGHTS),
        )
    )
    return [
        RubricEvidence(score, kind, graded_at)
        for score, kind, graded_at in rows
        if score is not None and graded_at is not None
    ]


def speaking_evidence(session: Session, user_id: int) -> list[RubricEvidence]:
    """Only sessions held at exam pace with the transcript hidden count, at drill weight."""
    rows = session.execute(
        select(WritingSubmission.score, WritingSubmission.graded_at)
        .join(AssessmentRun, AssessmentRun.id == WritingSubmission.run_id)
        .where(
            WritingSubmission.user_id == user_id,
            WritingSubmission.skill == "EO",
            WritingSubmission.status == "graded",
            AssessmentRun.result["exam"].as_boolean(),
        )
    )
    return [
        RubricEvidence(score, "drill", graded_at)
        for score, graded_at in rows
        if score is not None and graded_at is not None
    ]


def skill_level(session: Session, user_id: int, skill: str) -> SkillLevel | None:
    now = datetime.now(UTC)
    if skill == "EE":
        estimate = productive(writing_evidence(session, user_id), now)
    elif skill == "EO":
        estimate = productive(speaking_evidence(session, user_id), now)
    else:
        estimate = receptive(receptive_evidence(session, user_id, skill), now)
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
    if level is not None and skill in RECEPTIVE:
        return (level.estimate.score - tcf_from_theta(0)) / 100
    if level is not None:
        return CEFR_DIFFICULTY[level.cefr]
    view = load_path(session, user_id)
    current = next(
        (m.level_id for m in view.modules if view.status[m.id] == "open"),
        view.modules[-1].level_id if view.modules else "A1",
    )
    return CEFR_DIFFICULTY[current]
