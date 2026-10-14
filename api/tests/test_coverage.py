from app.domain.coverage import ModuleFacts, Status, coverage, statuses


def _facts(
    module_id: str,
    level: str = "A1",
    done: int = 0,
    score: float | None = None,
    placed: bool = False,
) -> ModuleFacts:
    return ModuleFacts(
        module_id, level, lessons_total=3, lessons_done=done, check_score=score, placed=placed
    )


def test_first_module_is_open_and_the_rest_locked() -> None:
    result = statuses([_facts("m1"), _facts("m2")])

    assert result == {"m1": Status.OPEN, "m2": Status.LOCKED}


def test_module_is_covered_only_with_all_lessons_and_passing_check() -> None:
    result = statuses([_facts("m1", done=3, score=0.8), _facts("m2", done=2, score=1.0)])

    assert result == {"m1": Status.COVERED, "m2": Status.OPEN}


def test_failing_check_keeps_module_open_and_next_locked() -> None:
    result = statuses([_facts("m1", done=3, score=0.7), _facts("m2")])

    assert result == {"m1": Status.OPEN, "m2": Status.LOCKED}


def test_placed_modules_count_as_done_and_unlock_the_next() -> None:
    ordered = [_facts("m1", placed=True), _facts("m2"), _facts("m3", level="A2")]
    result = statuses(ordered)
    cov = coverage(ordered, result)

    assert result["m2"] == Status.OPEN
    assert (cov.covered, cov.total, cov.percent) == (1, 3, 33.3)
    assert cov.by_level == {"A1": (1, 2), "A2": (0, 1)}
