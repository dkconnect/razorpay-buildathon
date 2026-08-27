from datetime import datetime, timedelta

from config.fraud import FraudRingConfig
from scenarios.fraud_ring import generate_fraud_ring


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


def test_combined_scenario_has_both_phases():
    transactions = generate_fraud_ring(
        make_config(),
        datetime(2026, 1, 5, 12, 0, 0),
    )

    phases = {
        transaction.phase
        for transaction in transactions
    }

    assert phases == {
        "testing",
        "bust_out",
    }


def test_combined_scenario_has_expected_count():
    config = make_config()

    transactions = generate_fraud_ring(
        config,
        datetime(2026, 1, 5, 12, 0, 0),
    )

    assert len(transactions) == (
        config.phase1_transaction_count
        + config.phase2_transaction_count
    )


def test_transactions_are_chronologically_sorted():
    transactions = generate_fraud_ring(
        make_config(),
        datetime(2026, 1, 5, 12, 0, 0),
    )

    timestamps = [
        transaction.timestamp
        for transaction in transactions
    ]

    assert timestamps == sorted(timestamps)


def test_phase_two_happens_after_phase_one():
    transactions = generate_fraud_ring(
        make_config(),
        datetime(2026, 1, 5, 12, 0, 0),
    )

    phase1 = [
        transaction.timestamp
        for transaction in transactions
        if transaction.phase == "testing"
    ]

    phase2 = [
        transaction.timestamp
        for transaction in transactions
        if transaction.phase == "bust_out"
    ]

    assert max(phase1) < min(phase2)


def test_gap_between_phases_is_respected():
    config = make_config()

    transactions = generate_fraud_ring(
        config,
        datetime(2026, 1, 5, 12, 0, 0),
    )

    phase1_end = max(
        transaction.timestamp
        for transaction in transactions
        if transaction.phase == "testing"
    )

    phase2_start = min(
        transaction.timestamp
        for transaction in transactions
        if transaction.phase == "bust_out"
    )

    minimum_gap = timedelta(
        minutes=config.phase2_gap_minutes
    )

    assert phase2_start >= phase1_end + minimum_gap


def test_all_transactions_belong_to_same_ring():
    transactions = generate_fraud_ring(
        make_config(),
        datetime(2026, 1, 5, 12, 0, 0),
    )

    ring_ids = {
        transaction.ring_id
        for transaction in transactions
    }

    assert ring_ids == {"ring_001"}


def test_phase_one_and_two_share_devices():
    transactions = generate_fraud_ring(
        make_config(),
        datetime(2026, 1, 5, 12, 0, 0),
    )

    phase1_devices = {
        transaction.device_id
        for transaction in transactions
        if transaction.phase == "testing"
    }

    phase2_devices = {
        transaction.device_id
        for transaction in transactions
        if transaction.phase == "bust_out"
    }

    assert phase1_devices & phase2_devices


def test_phase_one_and_two_share_ip_subnets():
    transactions = generate_fraud_ring(
        make_config(),
        datetime(2026, 1, 5, 12, 0, 0),
    )

    phase1_ips = {
        transaction.ip_subnet
        for transaction in transactions
        if transaction.phase == "testing"
    }

    phase2_ips = {
        transaction.ip_subnet
        for transaction in transactions
        if transaction.phase == "bust_out"
    }

    assert phase1_ips & phase2_ips


def test_phase_one_and_two_share_card_bins():
    transactions = generate_fraud_ring(
        make_config(),
        datetime(2026, 1, 5, 12, 0, 0),
    )

    phase1_bins = {
        transaction.card_bin
        for transaction in transactions
        if transaction.phase == "testing"
    }

    phase2_bins = {
        transaction.card_bin
        for transaction in transactions
        if transaction.phase == "bust_out"
    }

    assert phase1_bins & phase2_bins


def test_combined_scenario_is_reproducible():
    config = make_config()
    start = datetime(2026, 1, 5, 12, 0, 0)

    first = generate_fraud_ring(
        config,
        start,
        seed=99,
    )

    second = generate_fraud_ring(
        config,
        start,
        seed=99,
    )

    assert first == second