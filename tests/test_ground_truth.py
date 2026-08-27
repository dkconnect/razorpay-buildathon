from datetime import datetime

import pytest

from data.generator.ground_truth import (
    validate_fraud_ground_truth,
)
from scenarios.mixed_fraud import (
    generate_mixed_fraud_scenario,
)


def test_mixed_fraud_ground_truth_is_valid():
    transactions = generate_mixed_fraud_scenario(
        datetime(2026, 1, 5, 12, 0, 0),
        seed=42,
    )

    assert validate_fraud_ground_truth(
        transactions
    ) is True


def test_no_fraud_transactions_is_invalid():
    class Transaction:
        is_fraud = False
        ring_id = None
        phase = None

    with pytest.raises(ValueError):
        validate_fraud_ground_truth(
            [Transaction()]
        )


def test_invalid_phase_is_rejected():
    class Transaction:
        is_fraud = True
        ring_id = "ring_001"
        phase = "something_else"
        amount = 10

    with pytest.raises(ValueError):
        validate_fraud_ground_truth(
            [Transaction()]
        )


def test_testing_amount_is_validated():
    class Transaction:
        is_fraud = True
        ring_id = "ring_001"
        phase = "testing"
        amount = 500

    with pytest.raises(ValueError):
        validate_fraud_ground_truth(
            [Transaction()]
        )


def test_bust_out_amount_is_validated():
    class Transaction:
        is_fraud = True
        ring_id = "ring_001"
        phase = "bust_out"
        amount = 100

    with pytest.raises(ValueError):
        validate_fraud_ground_truth(
            [Transaction()]
        )