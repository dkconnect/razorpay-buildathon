from config.fraud import FraudRingConfig
from data.generator.fraud_identity import (
    FraudIdentity,
    generate_ring_identities,
)


def make_config():
    return FraudRingConfig(
        ring_id="ring_001",
        identity_count=10,
        phase1_duration_minutes=10,
        phase1_transaction_count=50,
        phase2_gap_minutes=5,
        phase2_duration_minutes=10,
        phase2_transaction_count=10,
    )


def test_generates_expected_number_of_identities():
    identities = generate_ring_identities(make_config())

    assert len(identities) == 10


def test_identity_fields_are_populated():
    identities = generate_ring_identities(make_config())

    for identity in identities:
        assert isinstance(identity, FraudIdentity)
        assert identity.device_id
        assert identity.ip_subnet
        assert identity.card_bin


def test_device_ids_are_unique():
    identities = generate_ring_identities(make_config())

    device_ids = [
        identity.device_id
        for identity in identities
    ]

    assert len(device_ids) == len(set(device_ids))


def test_identities_are_reproducible():
    first = generate_ring_identities(make_config())
    second = generate_ring_identities(make_config())

    assert first == second


def test_ring_id_is_embedded_in_identity():
    identities = generate_ring_identities(make_config())

    for identity in identities:
        assert "ring_001" in identity.device_id