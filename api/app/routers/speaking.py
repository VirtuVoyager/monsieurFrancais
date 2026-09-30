from fastapi import APIRouter, status

from app.db import SessionDep
from app.domain.speaking import TITLES
from app.schemas.learning import (
    RealtimeUsage,
    SdpOffer,
    SpeakingCallOut,
    SpeakingEnd,
    SpeakingSessionOut,
    SpeakingStart,
    SpeakingTaskOut,
    UsageVerdict,
)
from app.services import speaking
from app.services.skills import exam_scales
from app.services.users import CurrentUser

router = APIRouter(prefix="/speaking", tags=["speaking"])


@router.get("/tasks")
def list_tasks() -> list[SpeakingTaskOut]:
    return [_task(code) for code in exam_scales().speaking_tasks]


@router.post("/sessions")
def start_session(
    body: SpeakingStart, session: SessionDep, user: CurrentUser
) -> SpeakingSessionOut:
    run, item = speaking.start(session, user.id, body.task)
    return SpeakingSessionOut(run_id=run.id, task=_task(body.task), prompt=item.payload["prompt"])


@router.post("/sessions/{run_id}/call")
def connect(run_id: int, body: SdpOffer, session: SessionDep, user: CurrentUser) -> SpeakingCallOut:
    sdp, deadline = speaking.connect(session, user.id, run_id, body.sdp)
    return SpeakingCallOut(sdp=sdp, deadline=deadline)


@router.post("/sessions/{run_id}/usage")
def record_usage(
    run_id: int, body: RealtimeUsage, session: SessionDep, user: CurrentUser
) -> UsageVerdict:
    return UsageVerdict(stop=speaking.record(session, user.id, run_id, body.usage))


@router.post("/sessions/{run_id}/end", status_code=status.HTTP_204_NO_CONTENT)
def end_session(run_id: int, body: SpeakingEnd, session: SessionDep, user: CurrentUser) -> None:
    speaking.end(session, user.id, run_id, [line.model_dump() for line in body.transcript])


def _task(code: str) -> SpeakingTaskOut:
    spec = exam_scales().speaking_tasks[code]
    return SpeakingTaskOut(
        code=code, title=TITLES[code], prep_seconds=spec.prep_seconds, seconds=spec.seconds
    )
