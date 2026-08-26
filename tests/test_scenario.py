import pytest

from config.scenario import ScenarioConfig

def test_scenario_config():
    config = ScenarioConfig(
        name="normal_day",
        duration_minutes=120,
        base_rate_per_minute=10.0,
        seed=42,
    )

    assert config.name == "normal_day"
    assert config.duration_minutes == 120
    assert config.base_rate_per_minute == 10.0
    assert config.seed == 42


def test_invalid_duration():
    with pytest.raises(ValueError):
        ScenarioConfig(
            name="invalid",
            duration_minutes=0,
            base_rate_per_minute=10.0,
            seed=42,
        )


def test_invalid_rate():
    with pytest.raises(ValueError):
        ScenarioConfig(
            name="invalid",
            duration_minutes=120,
            base_rate_per_minute=0,
            seed=42,
        )


def test_config_is_immutable():
    config = ScenarioConfig(
        name="normal_day",
        duration_minutes=120,
        base_rate_per_minute=10.0,
        seed=42,
    )

    with pytest.raises(AttributeError):
        config.name = "changed"