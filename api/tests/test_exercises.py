import pytest

from app.domain.exercises import check, normalize, public

MCQ = {"kind": "mcq", "prompt": "Il ___ trente ans.", "options": ["est", "a"], "answer": 1}
CLOZE = {"kind": "cloze", "prompt": "Elle ___ Amina.", "accepted": ["s'appelle"]}
ORDER = {"kind": "order", "words": ["Nadia.", "m'appelle", "Je"], "answer": "Je m'appelle Nadia."}


def test_mcq_compares_choice_index() -> None:
    assert check(MCQ, {"choice": 1}).correct
    assert not check(MCQ, {"choice": 0}).correct
    assert check(MCQ, {"choice": 0}).expected == "a"


@pytest.mark.parametrize("text", ["s'appelle", "S’appelle", "  s'appelle  "])  # noqa: RUF001
def test_cloze_ignores_case_spacing_and_apostrophe_style(text: str) -> None:
    assert check(CLOZE, {"text": text}).correct


def test_cloze_accents_matter() -> None:
    cloze = {"kind": "cloze", "prompt": "Tu ___ ?", "accepted": ["es"]}

    assert not check(cloze, {"text": "és"}).correct


def test_order_ignores_final_punctuation() -> None:
    assert check(ORDER, {"text": "Je m'appelle Nadia"}).correct
    assert not check(ORDER, {"text": "Nadia je m'appelle"}).correct


def test_public_view_hides_answers() -> None:
    assert public({**MCQ, "explanation": "x"}) == {
        "kind": "mcq",
        "prompt": "Il ___ trente ans.",
        "options": ["est", "a"],
    }


def test_normalize_treats_non_breaking_space_as_space() -> None:
    assert normalize("Tu es prêt ?") == "tu es prêt"  # noqa: RUF001
