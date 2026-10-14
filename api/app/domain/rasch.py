import numpy as np

# Quadrature grid for expected-a-posteriori estimation; wide enough for A1 to C2 and beyond.
_GRID = np.linspace(-6.0, 6.0, 241)


def p_correct(theta: float, difficulty: float) -> float:
    return float(1.0 / (1.0 + np.exp(difficulty - theta)))


def estimate_ability(
    difficulties: list[float],
    correct: list[bool],
    weights: list[float],
    prior_mean: float = 0.0,
    prior_sd: float = 2.0,
) -> tuple[float, float]:
    """EAP ability and posterior SD under a Rasch model with weighted responses.

    EAP stays finite when every answer is right or wrong, which maximum likelihood does not.
    """
    b = np.asarray(difficulties)[:, None]
    y = np.asarray(correct, dtype=float)[:, None]
    w = np.asarray(weights)[:, None]
    p = 1.0 / (1.0 + np.exp(b - _GRID[None, :]))
    log_lik = (w * (y * np.log(p) + (1 - y) * np.log1p(-p))).sum(axis=0)
    log_post = log_lik - 0.5 * ((_GRID - prior_mean) / prior_sd) ** 2
    post = np.exp(log_post - log_post.max())
    post /= post.sum()
    mean = float((_GRID * post).sum())
    sd = float(np.sqrt(((_GRID - mean) ** 2 * post).sum()))
    return mean, sd
