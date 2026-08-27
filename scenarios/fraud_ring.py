from datetime import datetime

from config.fraud import FraudRingConfig
from data.generator.fraud_phase1 import (
    generate_phase1_transactions,
)
from data.generator.fraud_phase2 import (
    generate_phase2_transactions,
)


def generate_fraud_ring(
    config: FraudRingConfig,
    start_time: datetime,
    seed: int = 42,
):

    phase1 = generate_phase1_transactions(
        config=config,
        start_time=start_time,
        seed=seed,
    )

    if not phase1:
        return []

    phase1_end_time = max(
        transaction.timestamp
        for transaction in phase1
    )

    phase2 = generate_phase2_transactions(
        config=config,
        phase1_end_time=phase1_end_time,
        seed=seed + 1,
    )

    transactions = phase1 + phase2

    transactions.sort(
        key=lambda transaction: transaction.timestamp
    )

    return transactions