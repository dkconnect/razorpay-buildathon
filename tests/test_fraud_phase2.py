from datetime import datetime, timedelta

from config.fraud import FraudRingConfig
from data.generator.fraud_phase2 import (
    generate_phase2_transactions,
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


def test_phase2_generates_expected_count():
    transactions = generate_phase2_transactions(
        make_config(),
        datetime(2026, 1, 5, 12, 10, 0),
    )

    assert len(transactions) == 10


def test_phase2_transactions_are_fraud():
    transactions = generate_phase2_transactions(
        make_config(),
        datetime(2026, 1, 5, 12, 10, 0),
    )

    assert all(
        transaction.is_fraud
        for transaction in transactions
    )


def test_phase2_has_correct_labels():
    transactions = generate_phase2_transactions(
        make_config(),
        datetime(2026, 1, 5, 12, 10, 0),
    )

    assert all(
        transaction.ring_id == "ring_001"
        for transaction in transactions
    )

    assert all(
        transaction.phase == "bust_out"
        for transaction in transactions
    )


def test_phase2_amounts_are_high():
    config = make_config()

    transactions = generate_phase2_transactions(
        config,
        datetime(2026, 1, 5, 12, 10, 0),
    )

    assert all(
        config.phase2_min_amount
        <= transaction.amount
        <= config.phase2_max_amount
        for transaction in transactions
    )


def test_phase2_respects_gap_and_duration():
    config = make_config()

    phase1_end = datetime(
        2026,
        1,
        5,
        12,
        10,
        0,
    )

    expected_start = (
        phase1_end
        + timedelta(
            minutes=config.phase2_gap_minutes
        )
    )

    expected_end = (
        expected_start
        + timedelta(
            minutes=config.phase2_duration_minutes
        )
    )

    transactions = generate_phase2_transactions(
        config,
        phase1_end,
    )

    assert all(
        expected_start <= transaction.timestamp <= expected_end
        for transaction in transactions
    )


def test_phase2_reuses_ring_identity_pool():
    transactions = generate_phase2_transactions(
        make_config(),
        datetime(2026, 1, 5, 12, 10, 0),
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


def test_phase2_is_reproducible():
    config = make_config()

    phase1_end = datetime(
        2026,
        1,
        5,
        12,
        10,
        0,
    )

    first = generate_phase2_transactions(
        config,
        phase1_end,
        seed=123,
    )

    second = generate_phase2_transactions(
        config,
        phase1_end,
        seed=123,
    )

    assert first == second