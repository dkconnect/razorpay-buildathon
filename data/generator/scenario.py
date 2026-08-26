from datetime import datetime

from config.scenario import ScenarioConfig
from data.generator.merchant import generate_merchant_stream


DEFAULT_START_TIME = datetime(2026, 1, 5, 0, 0, 0)


def generate_scenario(
    config: ScenarioConfig,
    start_time=DEFAULT_START_TIME,
):
    transactions = generate_merchant_stream(
        start_time=start_time,
        duration_minutes=config.duration_minutes,
        base_rate_per_minute=config.base_rate_per_minute,
        seed=config.seed,
    )

    for transaction in transactions:
        transaction.scenario_id = config.name

    return transactions