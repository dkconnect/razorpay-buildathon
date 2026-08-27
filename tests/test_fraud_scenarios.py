from datetime import datetime

import pytest

from data.generator.fraud_scenarios import (
    generate_fraud_scenarios,
)


def test_generates_requested_number_of_scenarios():
    scenarios = generate_fraud_scenarios(
        count=5,
        start_time=datetime(2026, 1, 5, 12, 0, 0),
    )

    assert len(scenarios) == 5


def test_each_scenario_contains_transactions():
    scenarios = generate_fraud_scenarios(
        count=5,
        start_time=datetime(2026, 1, 5, 12, 0, 0),
    )

    assert all(
        len(transactions) > 0
        for transactions in scenarios
    )


def test_each_scenario_has_unique_ring_id():
    scenarios = generate_fraud_scenarios(
        count=5,
        start_time=datetime(2026, 1, 5, 12, 0, 0),
    )

    ring_ids = {
        transaction.ring_id
        for scenario in scenarios
        for transaction in scenario
    }

    assert ring_ids == {
        "ring_000",
        "ring_001",
        "ring_002",
        "ring_003",
        "ring_004",
    }


def test_each_scenario_contains_both_phases():
    scenarios = generate_fraud_scenarios(
        count=5,
        start_time=datetime(2026, 1, 5, 12, 0, 0),
    )

    for transactions in scenarios:
        phases = {
            transaction.phase
            for transaction in transactions
        }

        assert phases == {
            "testing",
            "bust_out",
        }


def test_all_generated_transactions_are_fraud():
    scenarios = generate_fraud_scenarios(
        count=5,
        start_time=datetime(2026, 1, 5, 12, 0, 0),
    )

    for transactions in scenarios:
        assert all(
            transaction.is_fraud
            for transaction in transactions
        )


def test_scenarios_are_reproducible():
    start = datetime(2026, 1, 5, 12, 0, 0)

    first = generate_fraud_scenarios(
        count=5,
        start_time=start,
        seed=100,
    )

    second = generate_fraud_scenarios(
        count=5,
        start_time=start,
        seed=100,
    )

    assert first == second


def test_different_seeds_produce_different_scenarios():
    start = datetime(2026, 1, 5, 12, 0, 0)

    first = generate_fraud_scenarios(
        count=5,
        start_time=start,
        seed=100,
    )

    second = generate_fraud_scenarios(
        count=5,
        start_time=start,
        seed=200,
    )

    assert first != second


def test_invalid_count():
    with pytest.raises(ValueError):
        generate_fraud_scenarios(
            count=0,
            start_time=datetime(
                2026,
                1,
                5,
                12,
                0,
                0,
            ),
        )