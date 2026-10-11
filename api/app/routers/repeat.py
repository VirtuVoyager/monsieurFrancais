from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.concurrency import run_in_threadpool

from app.db import SessionDep
from app.domain.pronunciation import MAX_ATTEMPTS
from app.errors import ForbiddenError
from app.llm.grader import ProviderUnavailableError
from app.schemas.learning import (
    RepeatAttemptOut,
    RepeatSentenceOut,
    RepeatSetDetail,
    RepeatSetOut,
    RepeatWordOut,
)
from app.services import audio, repeat
from app.services.users import CurrentUser

router = APIRouter(prefix="/repeat", tags=["repeat"])

# 20 s of 16 kHz 16-bit mono WAV is 640 KB.
MAX_WAV_BYTES = 1024 * 1024


@router.get("/sets")
def list_sets(session: SessionDep, _: CurrentUser) -> list[RepeatSetOut]:
    return [
        RepeatSetOut(id=s.id, title=s.title, focus=s.focus, cefr=s.cefr, sentences=n)
        for s, n in repeat.sets(session)
    ]


@router.get("/sets/{set_id}")
def get_set(set_id: str, session: SessionDep, _: CurrentUser) -> RepeatSetDetail:
    repeat_set, sentences = repeat.get_set(session, set_id)
    return RepeatSetDetail(
        id=repeat_set.id,
        title=repeat_set.title,
        focus=repeat_set.focus,
        max_attempts=MAX_ATTEMPTS,
        max_seconds=repeat.MAX_SECONDS,
        sentences=[
            RepeatSentenceOut(
                id=s.id,
                fr=s.fr,
                en=s.en,
                tip=s.tip,
                audio_url=audio.url_for(audio.repeat_request(s)),
            )
            for s in sentences
        ],
    )


@router.post("/sentences/{sentence_id}/attempts")
async def attempt(
    sentence_id: str,
    request: Request,
    session: SessionDep,
    user: CurrentUser,
    number: int = Query(alias="attempt"),
) -> RepeatAttemptOut:
    if request.headers.get("content-type", "").split(";")[0].strip() != "audio/wav":
        raise ForbiddenError("Expected a 16 kHz mono WAV recording")
    wav = await request.body()
    if not wav or len(wav) > MAX_WAV_BYTES:
        raise ForbiddenError("The recording is empty or too long")
    try:
        result = await run_in_threadpool(repeat.attempt, session, user.id, sentence_id, number, wav)
    except ProviderUnavailableError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    return RepeatAttemptOut(
        status=result.status,
        attempt=result.attempt,
        accuracy=result.accuracy,
        words=[
            RepeatWordOut(word=w.word, accuracy=w.accuracy, weak=weak) for w, weak in result.words
        ],
        feedback=result.feedback,
    )
