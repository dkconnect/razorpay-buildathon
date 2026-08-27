from datetime import datetime, timedelta

from config.fraud import FraudRingConfig
from data.generator.fraud_phase1 import (
    generate_phase1_transactions,
)


def make_config():
    return FraudRingConfig(
        ring_id="ring_001",
        identity_count=5,
        phase1_duration_minutes=10,
        phase1_transaction_count=50,
        phase2_gap_minutes=5,
        phase2_duration_minutes=10,
        phase2_transaction_count=10,
    )


def test_phase1_generates_expected_count():
    transactions = generate_phase1_transactions(
        make_config(),
        datetime(2026, 1, 5, 12, 0, 0),
    )

    assert len(transactions) == 50


def test_phase1_transactions_are_fraud():
    transactions = generate_phase1_transactions(
        make_config(),
        datetime(2026, 1, 5, 12, 0, 0),
    )

    assert all(
        transaction.is_fraud
        for transaction in transactions
    )


def test_phase1_has_correct_labels():
    transactions = generate_phase1_transactions(
        make_config(),
        datetime(2026, 1, 5, 12, 0, 0),
    )

    assert all(
        transaction.ring_id == "ring_001"
        for transaction in transactions
    )

    assert all(
        transaction.phase == "testing"
        for transaction in transactions
    )


def test_phase1_amounts_are_small():
    config = make_config()

    transactions = generate_phase1_transactions(
        config,
        datetime(2026, 1, 5, 12, 0, 0),
    )

    assert all(
        config.phase1_min_amount
        <= transaction.amount
        <= config.phase1_max_amount
        for transaction in transactions
    )


def test_phase1_stays_inside_time_window():
    config = make_config()

    start = datetime(2026, 1, 5, 12, 0, 0)

    end = start + timedelta(
        minutes=config.phase1_duration_minutes
    )

    transactions = generate_phase1_transactions(
        config,
        start,
    )

    assert all(
        start <= transaction.timestamp <= end
        for transaction in transactions
    )


def test_phase1_reuses_ring_identities():
    transactions = generate_phase1_transactions(
        make_config(),
        datetime(2026, 1, 5, 12, 0, 0),
    )

    device_ids = {
        transaction.device_id
        for transaction in transactions
    }

    ip_subnets = {
        transaction.ip_subnet
        for transaction in transactions
    }

    card_bins = {
        transaction.card_bin
        for transaction in transactions
    }

    assert len(device_ids) == 5
    assert len(ip_subnets) == 5
    assert len(card_bins) == 5


def test_phase1_is_reproducible():
    config = make_config()
    start = datetime(2026, 1, 5, 12, 0, 0)

    first = generate_phase1_transactions(
        config,
        start,
        seed=123,
    )

    second = generate_phase1_transactions(
        config,
        start,
        seed=123,
    )

    assert first == second