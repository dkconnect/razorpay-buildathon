from pathlib import Path

from data.io import load_transactions


DATASET = Path("data/generated/mixed_fraud.json")


def test_mixed_fraud_dataset_exists():
    assert DATASET.exists()


def test_mixed_fraud_dataset_has_expected_labels():
    transactions = load_transactions(DATASET)

    fraud = [
        transaction
        for transaction in transactions
        if transaction.is_fraud
    ]

    legitimate = [
        transaction
        for transaction in transactions
        if not transaction.is_fraud
    ]

    assert transactions
    assert fraud
    assert legitimate


def test_mixed_fraud_dataset_has_both_phases():
    transactions = load_transactions(DATASET)

    phases = {
        transaction.phase
        for transaction in transactions
        if transaction.is_fraud
    }

    assert phases == {
        "testing",
        "bust_out",
    }


def test_mixed_fraud_dataset_is_chronological():
    transactions = load_transactions(DATASET)

    timestamps = [
        transaction.timestamp
        for transaction in transactions
    ]

    assert timestamps == sorted(timestamps)


def test_mixed_fraud_dataset_has_expected_counts():
    transactions = load_transactions(DATASET)

    fraud = [
        transaction
        for transaction in transactions
        if transaction.is_fraud
    ]

    testing = [
        transaction
        for transaction in fraud
        if transaction.phase == "testing"
    ]

    bust_out = [
        transaction
        for transaction in fraud
        if transaction.phase == "bust_out"
    ]

    assert len(transactions) == 11944
    assert len(fraud) == 45
    assert len(testing) == 33
    assert len(bust_out) == 12