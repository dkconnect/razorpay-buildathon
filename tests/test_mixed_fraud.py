from datetime import datetime

from scenarios.mixed_fraud import (
    generate_mixed_fraud_scenario,
)


def test_mixed_scenario_contains_legitimate_and_fraud():
    transactions = generate_mixed_fraud_scenario(
        datetime(2026, 1, 5, 12, 0, 0),
    )

    assert any(
        not transaction.is_fraud
        for transaction in transactions
    )

    assert any(
        transaction.is_fraud
        for transaction in transactions
    )


def test_mixed_scenario_contains_both_fraud_phases():
    transactions = generate_mixed_fraud_scenario(
        datetime(2026, 1, 5, 12, 0, 0),
    )

    fraud_phases = {
        transaction.phase
        for transaction in transactions
        if transaction.is_fraud
    }

    assert fraud_phases == {
        "testing",
        "bust_out",
    }


def test_legitimate_transactions_have_no_ring_id():
    transactions = generate_mixed_fraud_scenario(
        datetime(2026, 1, 5, 12, 0, 0),
    )

    legitimate = [
        transaction
        for transaction in transactions
        if not transaction.is_fraud
    ]

    assert legitimate

    assert all(
        transaction.ring_id is None
        for transaction in legitimate
    )


def test_fraud_transactions_have_ring_id():
    transactions = generate_mixed_fraud_scenario(
        datetime(2026, 1, 5, 12, 0, 0),
    )

    fraud = [
        transaction
        for transaction in transactions
        if transaction.is_fraud
    ]

    assert fraud

    assert all(
        transaction.ring_id is not None
        for transaction in fraud
    )


def test_mixed_stream_is_chronologically_sorted():
    transactions = generate_mixed_fraud_scenario(
        datetime(2026, 1, 5, 12, 0, 0),
    )

    timestamps = [
        transaction.timestamp
        for transaction in transactions
    ]

    assert timestamps == sorted(timestamps)


def test_mixed_scenario_is_reproducible():
    start = datetime(2026, 1, 5, 12, 0, 0)

    first = generate_mixed_fraud_scenario(
        start,
        seed=123,
    )

    second = generate_mixed_fraud_scenario(
        start,
        seed=123,
    )

    assert first == second


def test_mixed_scenario_has_more_transactions_than_baseline():
    from scenarios.normal_day import generate_normal_day

    baseline = generate_normal_day()

    mixed = generate_mixed_fraud_scenario(
        datetime(2026, 1, 5, 12, 0, 0),
        seed=42,
    )

    assert len(mixed) > len(baseline)