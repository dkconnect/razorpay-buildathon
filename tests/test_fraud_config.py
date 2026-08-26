import pytest

from config.fraud import FraudRingConfig


def make_valid_config():
    return FraudRingConfig(
        ring_id="ring_001",
        identity_count=10,
        phase1_duration_minutes=10,
        phase1_transaction_count=50,
        phase2_gap_minutes=5,
        phase2_duration_minutes=10,
        phase2_transaction_count=10,
    )


def test_valid_fraud_ring_config():
    config = make_valid_config()

    assert config.ring_id == "ring_001"
    assert config.identity_count == 10
    assert config.phase1_transaction_count == 50
    assert config.phase2_transaction_count == 10


def test_identity_count_must_be_at_least_two():
    with pytest.raises(ValueError):
        FraudRingConfig(
            ring_id="ring_001",
            identity_count=1,
            phase1_duration_minutes=10,
            phase1_transaction_count=50,
            phase2_gap_minutes=5,
            phase2_duration_minutes=10,
            phase2_transaction_count=10,
        )


def test_phase1_amount_range_is_valid():
    with pytest.raises(ValueError):
        FraudRingConfig(
            ring_id="ring_001",
            identity_count=10,
            phase1_duration_minutes=10,
            phase1_transaction_count=50,
            phase2_gap_minutes=5,
            phase2_duration_minutes=10,
            phase2_transaction_count=10,
            phase1_min_amount=50,
            phase1_max_amount=10,
        )


def test_phase2_amount_range_is_valid():
    with pytest.raises(ValueError):
        FraudRingConfig(
            ring_id="ring_001",
            identity_count=10,
            phase1_duration_minutes=10,
            phase1_transaction_count=50,
            phase2_gap_minutes=5,
            phase2_duration_minutes=10,
            phase2_transaction_count=10,
            phase2_min_amount=50000,
            phase2_max_amount=5000,
        )


def test_config_is_immutable():
    config = make_valid_config()

    with pytest.raises(AttributeError):
        config.ring_id = "changed"