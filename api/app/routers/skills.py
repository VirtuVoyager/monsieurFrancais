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
    PlacementOutcome,
    SkillLevelOut,
)
from app.services import drills, placement, skills
from app.services.skills import SkillLevel
from app.services.users import CurrentUser

router = APIRouter(tags=["skills"])


@router.get("/skills")
def get_skills(session: SessionDep, user: CurrentUser) -> dict[str, SkillLevelOut | None]:
    return {skill: level_out(level) for skill, level in skills.all_levels(session, user.id).items()}


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
        level=level_out(skills.skill_level(session, user.id, grade.skills[0])),
    )


@router.post("/placement")
def start_placement(session: SessionDep, user: CurrentUser) -> DrillOut:
    run, items = placement.start(session, user.id)
    return DrillOut(
        run_id=run.id,
        skill=run.scope_id or "",
        deadline=drills.deadline_of(run),
        items=[CheckItemOut(id=i.id, skill=i.skill, exercise=_exam_exercise(i)) for i in items],
    )


@router.post("/placement/{run_id}")
def submit_placement(
    run_id: int, submission: CheckSubmission, session: SessionDep, user: CurrentUser
) -> PlacementOutcome:
    result = placement.submit(session, user.id, run_id, submission.answers)
    return PlacementOutcome(
        score=result.grade.score,
        placed_level=result.placed_level,
        modules_placed=result.modules_placed,
        levels={skill: level_out(level) for skill, level in result.levels.items()},
    )


def _exam_exercise(item: Item) -> ExerciseOut:
    exercise = public({"kind": item.kind, **item.payload})
    if item.audio_hash:
        # Recorded audio exists, so the script must not reach the browser.
        exercise.pop("audio_text", None)
        h = item.audio_hash
        exercise["audio_url"] = f"/media/catalog/audio/{h[:2]}/{h[2:4]}/{h}.opus"
    return ExerciseOut.model_validate(exercise)


def level_out(level: SkillLevel | None) -> SkillLevelOut | None:
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
