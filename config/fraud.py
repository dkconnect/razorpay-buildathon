from dataclasses import dataclass


@dataclass(frozen=True)
class FraudRingConfig:
    ring_id: str

    identity_count: int

    phase1_duration_minutes: int
    phase1_transaction_count: int

    phase2_gap_minutes: int
    phase2_duration_minutes: int
    phase2_transaction_count: int

    phase1_min_amount: float = 1.0
    phase1_max_amount: float = 50.0

    phase2_min_amount: float = 5000.0
    phase2_max_amount: float = 50000.0

    def __post_init__(self):
        if not self.ring_id:
            raise ValueError("ring_id must not be empty")

        if self.identity_count < 2:
            raise ValueError(
                "identity_count must be at least 2"
            )

        if self.phase1_duration_minutes <= 0:
            raise ValueError(
                "phase1_duration_minutes must be positive"
            )

        if self.phase1_transaction_count <= 0:
            raise ValueError(
                "phase1_transaction_count must be positive"
            )

        if self.phase2_gap_minutes < 0:
            raise ValueError(
                "phase2_gap_minutes cannot be negative"
            )

        if self.phase2_duration_minutes <= 0:
            raise ValueError(
                "phase2_duration_minutes must be positive"
            )

        if self.phase2_transaction_count <= 0:
            raise ValueError(
                "phase2_transaction_count must be positive"
            )

        if self.phase1_min_amount <= 0:
            raise ValueError(
                "phase1_min_amount must be positive"
            )

        if self.phase1_max_amount < self.phase1_min_amount:
            raise ValueError(
                "phase1_max_amount must be >= phase1_min_amount"
            )

        if self.phase2_min_amount <= 0:
            raise ValueError(
                "phase2_min_amount must be positive"
            )

        if self.phase2_max_amount < self.phase2_min_amount:
            raise ValueError(
                "phase2_max_amount must be >= phase2_min_amount"
            )