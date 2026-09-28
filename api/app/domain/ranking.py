RRF_K = 60  # standard reciprocal-rank-fusion constant; dampens the weight of top ranks


def reciprocal_rank_fusion(*rankings: list[str]) -> list[str]:
    """Merges ranked id lists; items found by several rankers rise to the top."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, key in enumerate(ranking):
            scores[key] = scores.get(key, 0.0) + 1.0 / (RRF_K + rank + 1)
    return sorted(scores, key=lambda key: scores[key], reverse=True)
