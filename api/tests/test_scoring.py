from datetime import UTC, datetime, timedelta

import pytest

from app.config import get_settings
from app.domain.rasch import estimate_ability, p_correct
from app.domain.scales import CEFR_DIFFICULTY, load_exam_scales, tcf_from_theta
from app.domain.skill_estimate import ItemEvidence, RubricEvidence, productive, receptive

NOW = datetime(2026, 9, 28, tzinfo=UTC)
SCALES = load_exam_scales(get_settings().content_dir / "exam_scales.yaml")


def test_learner_at_item_difficulty_has_even_odds() -> None:
    assert p_correct(0.5, 0.5) == pytest.approx(0.5)


def test_more_correct_answers_raise_ability() -> None:
    b = [CEFR_DIFFICULTY["B1"]] * 10
    low, _ = estimate_ability(b, [True] * 3 + [False] * 7, [1.0] * 10)
    high, _ = estimate_ability(b, [True] * 8 + [False] * 2, [1.0] * 10)

    assert high > low


def test_all_correct_stays_finite_and_uncertain() -> None:
    theta, sd = estimate_ability([0.0] * 3, [True] * 3, [1.0] * 3)

    assert 0 < theta < 6
    assert sd > 0.8


def test_more_evidence_narrows_uncertainty() -> None:
    _, sd_small = estimate_ability([0.0] * 5, [True, False] * 2 + [True], [1.0] * 5)
    _, sd_large = estimate_ability([0.0] * 40, [True, False] * 20, [1.0] * 40)

    assert sd_large < sd_small


def test_tcf_scale_matches_cefr_band_centres() -> None:
    assert tcf_from_theta(CEFR_DIFFICULTY["B2"]) == 450
    assert tcf_from_theta(10) == 699
    assert tcf_from_theta(-10) == 100


@pytest.mark.parametrize(
    ("skill", "score", "cefr", "nclc"),
    [
        ("CO", 458, "B2", 7),
        ("CO", 457, "B2", 6),
        ("CE", 452, "B2", 6),
        ("EE", 10, "B2", 7),
        ("EO", 9, "B1", 6),
        ("EO", 3, "A1", None),
        ("CE", 650, "C2", 10),
    ],
)
def test_exam_scale_lookups(skill: str, score: float, cefr: str, nclc: int | None) -> None:
    assert SCALES.cefr(skill, score) == cefr
    assert SCALES.nclc(skill, score) == nclc


def _items(correct: list[bool], at: datetime, source: str = "checkpoint") -> list[ItemEvidence]:
    return [ItemEvidence(CEFR_DIFFICULTY["B1"], c, source, at) for c in correct]


def test_receptive_estimate_lands_in_the_right_band() -> None:
    estimate = receptive(_items([True, False] * 15, NOW), NOW)

    assert estimate is not None
    assert SCALES.cefr("CO", estimate.score) == "B1"
    assert not estimate.stale


def test_old_evidence_widens_uncertainty_without_moving_the_score() -> None:
    evidence = _items([True, False] * 15, NOW - timedelta(days=60))
    fresh = receptive(evidence, NOW - timedelta(days=60))
    stale = receptive(evidence, NOW)

    assert fresh is not None and stale is not None
    assert stale.score == fresh.score
    assert stale.se > fresh.se
    assert stale.stale


def test_recent_evidence_outweighs_older_evidence() -> None:
    evidence = _items([False] * 20, NOW - timedelta(days=63)) + _items([True] * 20, NOW)

    estimate = receptive(evidence, NOW)

    assert estimate is not None and estimate.score > tcf_from_theta(CEFR_DIFFICULTY["B1"])


def test_drills_count_half_as_much_as_checkpoints() -> None:
    checkpoint = [RubricEvidence(12, "checkpoint", NOW)]
    drill = [RubricEvidence(6, "drill", NOW)]

    estimate = productive(checkpoint + drill, NOW)

    assert estimate is not None and estimate.score == pytest.approx(10)


def test_single_rubric_score_has_default_uncertainty() -> None:
    estimate = productive([RubricEvidence(11, "level_exam", NOW)], NOW)

    assert estimate is not None
    assert (estimate.score, estimate.se, estimate.evidence_count) == (11, 2.0, 1)


def test_no_evidence_means_no_estimate() -> None:
    assert receptive([], NOW) is None
    assert productive([], NOW) is None
