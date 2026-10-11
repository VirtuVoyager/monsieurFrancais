from dataclasses import asdict, dataclass
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.pronunciation import (
    MAX_ATTEMPTS,
    Assessment,
    WordScore,
    finished,
    flagged,
    marked,
    passed,
)
from app.errors import ForbiddenError, NotFoundError
from app.llm import get_coach
from app.llm.coach import fallback
from app.llm.grader import ProviderUnavailableError
from app.models import RepeatAttempt, RepeatSentence, RepeatSet
from app.services import budget, metering
from app.services.budget import BudgetExceededError
from app.speech import get_assessor

MAX_SECONDS = 20  # the recorder stops itself here; the longest sentence takes about 5 s
COACH_TOKENS = {"input_tokens": 1500.0, "output_tokens": 1000.0}


@dataclass(frozen=True)
class AttemptResult:
    # retry: try again; next: out of attempts; unheard: nothing to score, the try is not used.
    status: Literal["passed", "retry", "next", "unheard"]
    attempt: int
    accuracy: float
    words: list[tuple[WordScore, bool]]
    feedback: str


def sets(session: Session) -> list[tuple[RepeatSet, int]]:
    counts = (
        select(RepeatSet, func.count(RepeatSentence.id))
        .join(RepeatSentence, RepeatSentence.set_id == RepeatSet.id)
        .group_by(RepeatSet.id)
        .order_by(RepeatSet.order)
    )
    return [(s, n) for s, n in session.execute(counts)]


def get_set(session: Session, set_id: str) -> tuple[RepeatSet, list[RepeatSentence]]:
    repeat_set = session.get(RepeatSet, set_id)
    if repeat_set is None:
        raise NotFoundError("No such set")
    sentences = session.scalars(
        select(RepeatSentence).where(RepeatSentence.set_id == set_id).order_by(RepeatSentence.order)
    )
    return repeat_set, list(sentences)


def attempt(
    session: Session, user_id: int, sentence_id: str, number: int, wav: bytes
) -> AttemptResult:
    """Scores one try; the client runs the loop and moves on after MAX_ATTEMPTS."""
    sentence = session.get(RepeatSentence, sentence_id)
    if sentence is None:
        raise NotFoundError("No such sentence")
    if not 1 <= number <= MAX_ATTEMPTS:
        raise ForbiddenError(f"Each sentence has {MAX_ATTEMPTS} attempts")

    assessor = get_assessor()
    assessment = metering.run_metered(
        session,
        user_id=user_id,
        feature="pronunciation",
        model=assessor.model,
        estimate_usd=budget.price_book()
        .for_model(assessor.model)
        .cost({"audio_seconds": float(MAX_SECONDS)}),
        call=lambda: assessor.assess(wav, sentence.fr),
    )
    if not assessment.heard:
        session.commit()
        return AttemptResult("unheard", number, 0, [], "")

    ok = passed(assessment)
    weak = flagged(assessment)
    feedback = "" if ok else _coach(session, user_id, sentence, weak, number)
    session.add(
        RepeatAttempt(
            user_id=user_id,
            sentence_id=sentence.id,
            reference=sentence.fr,
            attempt=number,
            accuracy=assessment.accuracy,
            passed=ok,
            scores=_scores(assessment),
            feedback=feedback,
        )
    )
    session.commit()
    status: Literal["passed", "retry", "next"] = (
        "passed" if ok else "next" if finished(number, ok) else "retry"
    )
    return AttemptResult(status, number, assessment.accuracy, marked(assessment), feedback)


def _coach(
    session: Session, user_id: int, sentence: RepeatSentence, weak: list[WordScore], number: int
) -> str:
    coach = get_coach()
    try:
        return metering.run_metered(
            session,
            user_id=user_id,
            feature="pronunciation",
            model=coach.model,
            estimate_usd=budget.price_book().for_model(coach.model).cost(COACH_TOKENS),
            call=lambda: coach.coach(sentence.fr, sentence.tip, weak, number),
        )
    except (BudgetExceededError, ProviderUnavailableError):
        # The scores are already paid for; a plain pointer keeps the loop useful.
        return fallback(weak)


def _scores(assessment: Assessment) -> dict[str, object]:
    return {
        "fluency": assessment.fluency,
        "completeness": assessment.completeness,
        "words": [asdict(w) for w in assessment.words],
    }
