from data.generator.fraud_config import (
    generate_random_fraud_config,
)


def test_random_config_returns_valid_config():
    config = generate_random_fraud_config(
        seed=42,
        ring_id="ring_001",
    )

    assert config.ring_id == "ring_001"
    assert config.identity_count >= 4
    assert config.identity_count <= 14

    assert config.phase1_duration_minutes >= 5
    assert config.phase1_duration_minutes <= 20

    assert config.phase1_transaction_count >= 30
    assert config.phase1_transaction_count <= 150

    assert config.phase2_gap_minutes >= 2
    assert config.phase2_gap_minutes <= 15

    assert config.phase2_duration_minutes >= 5
    assert config.phase2_duration_minutes <= 15

    assert config.phase2_transaction_count >= 5
    assert config.phase2_transaction_count <= 30


def test_random_config_is_reproducible():
    first = generate_random_fraud_config(
        seed=123,
        ring_id="ring_001",
    )

    second = generate_random_fraud_config(
        seed=123,
        ring_id="ring_001",
    )

    assert first == second


def test_different_seeds_can_produce_different_configs():
    first = generate_random_fraud_config(
        seed=1,
        ring_id="ring_001",
    )

    second = generate_random_fraud_config(
        seed=2,
        ring_id="ring_001",
    )

    assert first != second


def test_ring_id_is_preserved():
    config = generate_random_fraud_config(
        seed=42,
        ring_id="ring_special",
    )

    assert config.ring_id == "ring_special"