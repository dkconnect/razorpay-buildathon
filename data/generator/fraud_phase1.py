from datetime import timedelta
import random

from config.fraud import FraudRingConfig
from data.generator.fraud_identity import generate_ring_identities
from data.schema import Transaction


def generate_phase1_transactions(
    config: FraudRingConfig,
    start_time,
    seed: int = 42,
):

# generates car testing transactions for a fraud ring

    rng = random.Random(seed)

    identities = generate_ring_identities(config)

    transactions = []

    for index in range(config.phase1_transaction_count):
        identity = identities[
            index % len(identities)
        ]

        elapsed_seconds = rng.uniform(
            0,
            config.phase1_duration_minutes * 60,
        )

        timestamp = (
            start_time
            + timedelta(seconds=elapsed_seconds)
        )

        amount = round(
            rng.uniform(
                config.phase1_min_amount,
                config.phase1_max_amount,
            ),
            2,
        )

        transactions.append(
            Transaction(
                transaction_id=(
                    f"{config.ring_id}_testing_{index}"
                ),
                timestamp=timestamp,
                amount=amount,
                customer_id=(
                    f"{config.ring_id}_customer_{index}"
                ),
                device_id=identity.device_id,
                ip_subnet=identity.ip_subnet,
                card_bin=identity.card_bin,
                is_fraud=True,
                ring_id=config.ring_id,
                phase="testing",
                scenario_id="fraud_ring",
            )
        )

    transactions.sort(
        key=lambda transaction: transaction.timestamp
    )

    return transactions