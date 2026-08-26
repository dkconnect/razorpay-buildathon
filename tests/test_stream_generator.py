from datetime import datetime

from data.generator.stream import (
    generate_poisson_stream,
    generate_stream,
)

def test_generate_stream():
    start_time = datetime(2026, 1, 1, 12, 0, 0)

    transactions = generate_stream(
        start_time=start_time,
        num_transactions=5,
        interval_seconds=10,
    )

    assert len(transactions) == 5

    for tx in transactions:
        assert tx.is_fraud is False

    for i in range(1, len(transactions)):
        assert (
            transactions[i].timestamp
            > transactions[i - 1].timestamp
        )

    assert (
        transactions[1].timestamp
        - transactions[0].timestamp
    ).total_seconds() == 10

def test_generate_poisson_stream():
    start_time = datetime(2026, 1, 1, 12, 0, 0)

    transactions = generate_poisson_stream(
        start_time=start_time,
        num_transactions=100,
        rate_per_minute=10,
        seed=42,
    )

    assert len(transactions) == 100

    for tx in transactions:
        assert tx.timestamp >= start_time
        assert tx.is_fraud is False

    for i in range(1, len(transactions)):
        assert (
            transactions[i].timestamp
            > transactions[i - 1].timestamp
        )

def test_poisson_stream_is_reproducible():
    start_time = datetime(2026, 1, 1, 12, 0, 0)

    first = generate_poisson_stream(
        start_time=start_time,
        num_transactions=50,
        rate_per_minute=10,
        seed=42,
    )

    second = generate_poisson_stream(
        start_time=start_time,
        num_transactions=50,
        rate_per_minute=10,
        seed=42,
    )

    first_times = [tx.timestamp for tx in first]
    second_times = [tx.timestamp for tx in second]

    assert first_times == second_times

def test_poisson_stream_has_realistic_amounts():
    start_time = datetime(2026, 1, 1, 12, 0, 0)

    transactions = generate_poisson_stream(
        start_time=start_time,
        num_transactions=1000,
        rate_per_minute=10,
        seed=42,
    )

    amounts = [tx.amount for tx in transactions]

    assert all(amount > 0 for amount in amounts)

    # right-skewed distribution where the mean is above the median.
    import numpy as np

    assert np.mean(amounts) > np.median(amounts)