from fastapi import APIRouter

from app.db import SessionDep
from app.domain.exercises import public
from app.models import Item
from app.schemas.learning import (
    CheckItemOut,
    CheckSubmission,
    DrillOut,
    DrillOutcome,
    DrillStart,
    ExerciseOut,
    ItemResult,
    SkillLevelOut,
)
from app.services import drills, skills
from app.services.skills import SkillLevel
from app.services.users import CurrentUser

router = APIRouter(tags=["skills"])


@router.get("/skills")
def get_skills(session: SessionDep, user: CurrentUser) -> dict[str, SkillLevelOut | None]:
    return {
        skill: _level_out(level) for skill, level in skills.all_levels(session, user.id).items()
    }


@router.post("/drills")
def start_drill(body: DrillStart, session: SessionDep, user: CurrentUser) -> DrillOut:
    run, items = drills.start(session, user.id, body.skill, body.count)
    return DrillOut(
        run_id=run.id,
        skill=body.skill,
        deadline=drills.deadline_of(run),
        items=[CheckItemOut(id=i.id, skill=i.skill, exercise=_exam_exercise(i)) for i in items],
    )


@router.post("/drills/{run_id}")
def submit_drill(
    run_id: int, submission: CheckSubmission, session: SessionDep, user: CurrentUser
) -> DrillOutcome:
    grade = drills.submit(session, user.id, run_id, submission.answers)
    return DrillOutcome(
        score=grade.score,
        results=[
            ItemResult(
                item_id=item_id, correct=r.correct, expected=r.expected, explanation=r.explanation
            )
            for item_id, r in grade.results
        ],
        level=_level_out(skills.skill_level(session, user.id, grade.skill)),
    )


def _exam_exercise(item: Item) -> ExerciseOut:
    exercise = public({"kind": item.kind, **item.payload})
    if item.audio_hash:
        # Recorded audio exists, so the script must not reach the browser.
        exercise.pop("audio_text", None)
        h = item.audio_hash
        exercise["audio_url"] = f"/media/catalog/audio/{h[:2]}/{h[2:4]}/{h}.opus"
    return ExerciseOut.model_validate(exercise)


def _level_out(level: SkillLevel | None) -> SkillLevelOut | None:
    if level is None:
        return None
    e = level.estimate
    return SkillLevelOut(
        skill=level.skill,
        score=round(e.score, 1),
        se=round(e.se, 1),
        cefr=level.cefr,
        nclc=level.nclc,
        evidence_count=e.evidence_count,
        last_at=e.last_at,
        stale=e.stale,
    )
