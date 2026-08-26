from dataclasses import dataclass

from config.fraud import FraudRingConfig


@dataclass(frozen=True)
class FraudIdentity:
    device_id: str
    ip_subnet: str
    card_bin: str


def generate_ring_identities(
    config: FraudRingConfig,
):
# generated synthetic identities for a fraud ring

    identities = []

    for index in range(config.identity_count):
        identities.append(
            FraudIdentity(
                device_id=f"fraud_device_{config.ring_id}_{index}",
                ip_subnet=f"10.250.{index}.0/24",
                card_bin=f"40000{index:02d}",
            )
        )

    return identities