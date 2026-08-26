import numpy as np
import pytest

from data.generator.amounts import generate_amounts


def test_generate_amounts():
    amounts = generate_amounts(
        num_transactions=1000,
        seed=42,
    )

    assert len(amounts) == 1000
    assert np.all(amounts > 0)


def test_amount_generation_is_reproducible():
    first = generate_amounts(
        num_transactions=100,
        seed=42,
    )

    second = generate_amounts(
        num_transactions=100,
        seed=42,
    )

    assert np.array_equal(first, second)


def test_invalid_sigma():
    with pytest.raises(ValueError):
        generate_amounts(
            num_transactions=10,
            sigma=0,
        )