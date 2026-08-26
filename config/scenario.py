from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioConfig:
    name: str
    duration_minutes: int
    base_rate_per_minute: float
    seed: int

    def __post_init__(self):
        if self.duration_minutes <= 0:
            raise ValueError(
                "duration_minutes must be positive"
            )

        if self.base_rate_per_minute <= 0:
            raise ValueError(
                "base_rate_per_minute must be positive"
            )