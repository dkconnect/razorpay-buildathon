import random

from config.fraud import FraudRingConfig


def generate_random_fraud_config(
    seed: int = 42,
    ring_id: str = "ring_random",
):

# generates a random fraud ring config\

    rng = random.Random(seed)

    identity_count = rng.randint(4, 14)

    phase1_duration = rng.randint(5, 20)
    phase1_count = rng.randint(30, 150)

    phase2_gap = rng.randint(2, 15)
    phase2_duration = rng.randint(5, 15)
    phase2_count = rng.randint(5, 30)

    return FraudRingConfig(
        ring_id=ring_id,
        identity_count=identity_count,
        phase1_duration_minutes=phase1_duration,
        phase1_transaction_count=phase1_count,
        phase2_gap_minutes=phase2_gap,
        phase2_duration_minutes=phase2_duration,
        phase2_transaction_count=phase2_count,
    )