from config.scenario import ScenarioConfig
from data.generator.scenario import generate_scenario


NORMAL_DAY_CONFIG = ScenarioConfig(
    name="normal_day",
    duration_minutes=24 * 60,
    base_rate_per_minute=10.0,
    seed=42,
)


def generate_normal_day():
# will give 1 day of legitimate merchant traffic
    return generate_scenario(NORMAL_DAY_CONFIG)