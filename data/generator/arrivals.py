import numpy as np


def generate_interarrival_times(
    num_transactions,
    rate_per_minute,
    seed=None,
):

#inter-arrivals 

    if num_transactions <= 0:
        return np.array([])

    if rate_per_minute <= 0:
        raise ValueError("rate_per_minute should be positive")

    rng = np.random.default_rng(seed)

    rate_per_second = rate_per_minute / 60.0

    return rng.exponential(
        scale=1.0 / rate_per_second,
        size=num_transactions,
    )