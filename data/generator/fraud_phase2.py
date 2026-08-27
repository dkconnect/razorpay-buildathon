from datetime import timedelta
import random

from config.fraud import FraudRingConfig
from data.generator.fraud_identity import generate_ring_identities
from data.schema import Transaction


def generate_phase2_transactions(
    config: FraudRingConfig,
    phase1_end_time,
    seed: int = 43,
):

# generates bust out transactions for a fraud ring

    rng = random.Random(seed)

    identities = generate_ring_identities(config)

    start_time = (
        phase1_end_time
        + timedelta(minutes=config.phase2_gap_minutes)
    )

    transactions = []

    for index in range(config.phase2_transaction_count):
        identity = identities[
            index % len(identities)
        ]

        elapsed_seconds = rng.uniform(
            0,
            config.phase2_duration_minutes * 60,
        )

        timestamp = (
            start_time
            + timedelta(seconds=elapsed_seconds)
        )

        amount = round(
            rng.uniform(
                config.phase2_min_amount,
                config.phase2_max_amount,
            ),
            2,
        )

        transactions.append(
            Transaction(
                transaction_id=(
                    f"{config.ring_id}_bustout_{index}"
                ),
                timestamp=timestamp,
                amount=amount,
                customer_id=(
                    f"{config.ring_id}_customer_bustout_{index}"
                ),
                device_id=identity.device_id,
                ip_subnet=identity.ip_subnet,
                card_bin=identity.card_bin,
                is_fraud=True,
                ring_id=config.ring_id,
                phase="bust_out",
                scenario_id="fraud_ring",
            )
        )

    transactions.sort(
        key=lambda transaction: transaction.timestamp
    )

    return transactions