from datetime import datetime, timedelta

from data.generator.fraud_config import (
    generate_random_fraud_config,
)
from scenarios.fraud_ring import generate_fraud_ring


def generate_fraud_scenarios(
    count: int,
    start_time: datetime,
    seed: int = 42,
):
# will generate multiple independent fraud ring scenarios

    if count <= 0:
        raise ValueError("count must be positive")

    scenarios = []

    for index in range(count):
        scenario_seed = seed + index

        config = generate_random_fraud_config(
            seed=scenario_seed,
            ring_id=f"ring_{index:03d}",
        )

        scenario_start = (
            start_time
            + timedelta(hours=index)
        )

        transactions = generate_fraud_ring(
            config=config,
            start_time=scenario_start,
            seed=scenario_seed,
        )

        scenarios.append(transactions)

    return scenarios