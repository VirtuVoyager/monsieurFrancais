import math
from dataclasses import dataclass
from datetime import datetime

from app.domain.rasch import estimate_ability
from app.domain.scales import tcf_from_theta

HALF_LIFE_DAYS = 21.0
STALE_AFTER_DAYS = 21.0
SOURCE_WEIGHTS = {"drill": 0.5, "checkpoint": 1.0, "level_exam": 1.0, "mock": 1.0, "placement": 1.0}
SINGLE_RUBRIC_SE = 2.0  # points on /20 when only one graded attempt exists


@dataclass(frozen=True)
class ItemEvidence:
    difficulty: float
    correct: bool
    source: str
    at: datetime


@dataclass(frozen=True)
class RubricEvidence:
    score: float
    source: str
    at: datetime


@dataclass(frozen=True)
class Estimate:
    score: float
    se: float
    evidence_count: int
    last_at: datetime
    stale: bool


def receptive(evidence: list[ItemEvidence], now: datetime) -> Estimate | None:
    """Listening/reading estimate on the TCF /699 scale."""
    if not evidence:
        return None
    last_at = max(e.at for e in evidence)
    weights = [SOURCE_WEIGHTS[e.source] * _recency(e.at, last_at) for e in evidence]
    theta, sd = estimate_ability(
        [e.difficulty for e in evidence], [e.correct for e in evidence], weights
    )
    score = tcf_from_theta(theta)
    return Estimate(
        score,
        100.0 * sd * _staleness(last_at, now),
        len(evidence),
        last_at,
        _is_stale(last_at, now),
    )


def productive(evidence: list[RubricEvidence], now: datetime) -> Estimate | None:
    """Writing/speaking estimate on the TCF /20 scale."""
    if not evidence:
        return None
    last_at = max(e.at for e in evidence)
    weights = [SOURCE_WEIGHTS[e.source] * _recency(e.at, last_at) for e in evidence]
    total = sum(weights)
    mean = sum(w * e.score for w, e in zip(weights, evidence, strict=True)) / total
    if len(evidence) == 1:
        se = SINGLE_RUBRIC_SE
    else:
        variance = sum(w * (e.score - mean) ** 2 for w, e in zip(weights, evidence, strict=True))
        effective_n = total**2 / sum(w * w for w in weights)
        se = max(math.sqrt(variance / total / effective_n), 0.5)
    return Estimate(
        mean, se * _staleness(last_at, now), len(evidence), last_at, _is_stale(last_at, now)
    )


def _recency(at: datetime, newest: datetime) -> float:
    # Relative to the newest evidence, so time passing alone never lowers the score.
    return float(0.5 ** ((newest - at).total_seconds() / 86400 / HALF_LIFE_DAYS))


def _staleness(last_at: datetime, now: datetime) -> float:
    # Old evidence widens the uncertainty band instead of moving the estimate.
    days = max((now - last_at).total_seconds() / 86400 - STALE_AFTER_DAYS, 0.0)
    return math.sqrt(2 ** (days / HALF_LIFE_DAYS))


def _is_stale(last_at: datetime, now: datetime) -> bool:
    return (now - last_at).total_seconds() / 86400 > STALE_AFTER_DAYS
