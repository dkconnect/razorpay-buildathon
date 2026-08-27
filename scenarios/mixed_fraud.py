from datetime import datetime

from data.generator.fraud_scenarios import (
    generate_fraud_scenarios,
)
from scenarios.normal_day import generate_normal_day


def generate_mixed_fraud_scenario(
    start_time: datetime,
    seed: int = 42,
):

    # scenario configuration.
    legitimate = generate_normal_day()

    fraud_scenarios = generate_fraud_scenarios(
        count=1,
        start_time=start_time,
        seed=seed,
    )

    fraud = fraud_scenarios[0]

    transactions = legitimate + fraud

    transactions.sort(
        key=lambda transaction: transaction.timestamp
    )

    return transactions