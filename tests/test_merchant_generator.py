from datetime import datetime

import pytest

from data.generator.merchant import generate_merchant_stream


def test_generate_merchant_stream():
    start_time = datetime(2026, 1, 5, 12, 0, 0)

    transactions = generate_merchant_stream(
        start_time=start_time,
        duration_minutes=60,
        base_rate_per_minute=10,
        seed=42,
    )

    assert len(transactions) > 0

    for tx in transactions:
        assert tx.timestamp >= start_time
        assert tx.timestamp < datetime(2026, 1, 5, 13, 0, 0)
        assert tx.amount > 0
        assert tx.is_fraud is False


def test_merchant_stream_is_chronological():
    start_time = datetime(2026, 1, 5, 12, 0, 0)

    transactions = generate_merchant_stream(
        start_time=start_time,
        duration_minutes=60,
        base_rate_per_minute=10,
        seed=42,
    )

    timestamps = [tx.timestamp for tx in transactions]

    assert timestamps == sorted(timestamps)


def test_merchant_stream_is_reproducible():
    start_time = datetime(2026, 1, 5, 12, 0, 0)

    first = generate_merchant_stream(
        start_time=start_time,
        duration_minutes=60,
        base_rate_per_minute=10,
        seed=42,
    )

    second = generate_merchant_stream(
        start_time=start_time,
        duration_minutes=60,
        base_rate_per_minute=10,
        seed=42,
    )

    assert first == second


def test_invalid_duration():
    with pytest.raises(ValueError):
        generate_merchant_stream(
            start_time=datetime(2026, 1, 5, 12, 0, 0),
            duration_minutes=0,
        )