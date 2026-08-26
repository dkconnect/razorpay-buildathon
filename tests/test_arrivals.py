import numpy as np
import pytest

from data.generator.arrivals import generate_interarrival_times


def test_interarrival_times_are_positive():
    times = generate_interarrival_times(
        num_transactions=100,
        rate_per_minute=10,
        seed=42,
    )

    assert len(times) == 100
    assert np.all(times > 0)


def test_seed_makes_generation_reproducible():
    first = generate_interarrival_times(
        num_transactions=100,
        rate_per_minute=10,
        seed=42,
    )

    second = generate_interarrival_times(
        num_transactions=100,
        rate_per_minute=10,
        seed=42,
    )

    assert np.array_equal(first, second)


def test_invalid_rate():
    with pytest.raises(ValueError):
        generate_interarrival_times(
            num_transactions=10,
            rate_per_minute=0,
        )