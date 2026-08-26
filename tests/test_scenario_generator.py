from datetime import datetime

from config.scenario import ScenarioConfig
from data.generator.scenario import generate_scenario


def test_generate_scenario():
    config = ScenarioConfig(
        name="normal_day",
        duration_minutes=60,
        base_rate_per_minute=10.0,
        seed=42,
    )

    transactions = generate_scenario(
        config,
        start_time=datetime(2026, 1, 5, 12, 0, 0),
    )

    assert len(transactions) > 0

    for transaction in transactions:
        assert transaction.scenario_id == "normal_day"
        assert transaction.is_fraud is False


def test_scenario_is_reproducible():
    config = ScenarioConfig(
        name="normal_day",
        duration_minutes=60,
        base_rate_per_minute=10.0,
        seed=42,
    )

    first = generate_scenario(
        config,
        start_time=datetime(2026, 1, 5, 12, 0, 0),
    )

    second = generate_scenario(
        config,
        start_time=datetime(2026, 1, 5, 12, 0, 0),
    )

    assert first == second