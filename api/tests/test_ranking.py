from app.domain.ranking import reciprocal_rank_fusion


def test_items_found_by_both_rankers_win() -> None:
    fused = reciprocal_rank_fusion(["a", "b", "c"], ["c", "d"])

    assert fused[0] == "c"
    assert set(fused) == {"a", "b", "c", "d"}


def test_single_ranking_keeps_its_order() -> None:
    assert reciprocal_rank_fusion(["x", "y", "z"]) == ["x", "y", "z"]
