from fastapi import APIRouter, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from app.db import SessionDep
from app.domain.speaking import TITLES, from_text
from app.errors import ForbiddenError
from app.models import AssessmentRun, WritingSubmission
from app.presenters import writing_result
from app.routers.skills import level_out
from app.schemas.learning import (
    RealtimeUsage,
    SdpOffer,
    SpeakingCallOut,
    SpeakingEnd,
    SpeakingResult,
    SpeakingSessionOut,
    SpeakingStart,
    SpeakingTaskOut,
    TranscriptLine,
    UsageVerdict,
)
from app.services import skills, speaking
from app.services.skills import exam_scales
from app.services.users import CurrentUser

router = APIRouter(prefix="/speaking", tags=["speaking"])

# A five-minute answer in Opus is around 2–3 MB; the cap only stops runaway uploads.
MAX_RECORDING_BYTES = 25 * 1024 * 1024


@router.get("/tasks")
def list_tasks() -> list[SpeakingTaskOut]:
    return [_task(code) for code in exam_scales().speaking_tasks]


@router.post("/sessions")
def start_session(
    body: SpeakingStart, session: SessionDep, user: CurrentUser
) -> SpeakingSessionOut:
    run, item = speaking.start(session, user.id, body.task, body.pace, body.show_transcript)
    return SpeakingSessionOut(
        run_id=run.id,
        task=_task(body.task),
        prompt=item.payload["prompt"],
        pace=body.pace,
        exam=run.result["exam"],
    )


@router.post("/sessions/{run_id}/call")
def connect(run_id: int, body: SdpOffer, session: SessionDep, user: CurrentUser) -> SpeakingCallOut:
    sdp, deadline = speaking.connect(session, user.id, run_id, body.sdp)
    return SpeakingCallOut(sdp=sdp, deadline=deadline)


@router.post("/sessions/{run_id}/usage")
def record_usage(
    run_id: int, body: RealtimeUsage, session: SessionDep, user: CurrentUser
) -> UsageVerdict:
    return UsageVerdict(stop=speaking.record(session, user.id, run_id, body.usage))


@router.post("/sessions/{run_id}/recording", status_code=status.HTTP_204_NO_CONTENT)
async def upload_recording(
    run_id: int, request: Request, session: SessionDep, user: CurrentUser
) -> None:
    mime = request.headers.get("content-type", "").split(";")[0].strip()
    if not mime.startswith("audio/"):
        raise ForbiddenError("Expected an audio recording")
    audio = await request.body()
    if not audio or len(audio) > MAX_RECORDING_BYTES:
        raise ForbiddenError("The recording is empty or too large")
    await run_in_threadpool(speaking.save_recording, session, user.id, run_id, audio, mime)


@router.post("/sessions/{run_id}/end")
def end_session(
    run_id: int, body: SpeakingEnd, session: SessionDep, user: CurrentUser
) -> SpeakingResult:
    lines = [line.model_dump() for line in body.transcript]
    submission = speaking.end(session, user.id, run_id, lines)
    run, _ = speaking.result(session, user.id, run_id)
    return _result(session, user.id, run, submission)


@router.get("/sessions/{run_id}")
def get_result(run_id: int, session: SessionDep, user: CurrentUser) -> SpeakingResult:
    run, submission = speaking.result(session, user.id, run_id)
    return _result(session, user.id, run, submission)


@router.get("/sessions/{run_id}/recording")
def get_recording(run_id: int, session: SessionDep, user: CurrentUser) -> FileResponse:
    path, mime = speaking.recording(session, user.id, run_id)
    return FileResponse(path, media_type=mime)


def _task(code: str) -> SpeakingTaskOut:
    spec = exam_scales().speaking_tasks[code]
    return SpeakingTaskOut(
        code=code, title=TITLES[code], prep_seconds=spec.prep_seconds, seconds=spec.seconds
    )


def _result(
    session: SessionDep, user_id: int, run: AssessmentRun, submission: WritingSubmission | None
) -> SpeakingResult:
    if submission and submission.text:
        transcript = [TranscriptLine(role=t.role, text=t.text) for t in from_text(submission.text)]
    else:
        transcript = [
            TranscriptLine.model_validate(line) for line in run.result.get("transcript", [])
        ]
    graded = submission is not None and submission.status == "graded"
    return SpeakingResult(
        run_id=run.id,
        task=run.result["task"],
        exam=run.result["exam"],
        status=submission.status if submission else "none",
        feedback=writing_result(submission) if submission and graded else None,
        transcript=transcript,
        has_recording="recording" in run.result,
        level=level_out(skills.skill_level(session, user_id, "EO"))
        if graded and run.result["exam"]
        else None,
    )
