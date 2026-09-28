import pytest

from app.domain.rubric import RubricPass, combine, needs_another_pass, word_count


def _pass(task: int, coherence: int, vocabulary: int, grammar: int) -> RubricPass:
    criteria = {"task": task, "coherence": coherence, "vocabulary": vocabulary, "grammar": grammar}
    return RubricPass(criteria=criteria, evidence={c: "…" for c in criteria})


def test_close_passes_do_not_need_a_third() -> None:
    assert not needs_another_pass([_pass(3, 3, 3, 3), _pass(3, 3, 3, 2)])


def test_disagreement_over_one_point_needs_a_third_pass() -> None:
    assert needs_another_pass([_pass(3, 3, 3, 3), _pass(2, 3, 3, 2)])


def test_combined_score_is_the_median_per_criterion() -> None:
    rubric = combine([_pass(5, 3, 3, 1), _pass(2, 3, 4, 2), _pass(3, 3, 3, 3)])

    assert rubric.criteria == {"task": 3, "coherence": 3, "vocabulary": 3, "grammar": 2}
    assert rubric.score == 11
    assert rubric.passes == 3


def test_combine_needs_at_least_one_pass() -> None:
    with pytest.raises(ValueError):
        combine([])


def test_word_count_splits_elisions() -> None:
    assert word_count("J'ai trente ans et l’école est loin.") == 9
