import numpy as np


def generate_amounts(
    num_transactions,
    mu=7.5,
    sigma=0.8,
    seed=None,
):

#generates legitimate transaction amounts

    if num_transactions <= 0:
        return np.array([])

    if sigma <= 0:
        raise ValueError("sigma should be positive")

    rng = np.random.default_rng(seed)

    amounts = rng.lognormal(
        mean=mu,
        sigma=sigma,
        size=num_transactions,
    )

    return np.round(amounts, 2)