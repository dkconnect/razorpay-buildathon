from dataclasses import dataclass
from datetime import datetime


@dataclass
class Transaction:
    transaction_id: str
    timestamp: datetime
    amount: float

    customer_id: str
    device_id: str
    ip_subnet: str
    card_bin: str

    # ground truth
    # i will only use them during data generation/evaluation.
    is_fraud: bool = False
    ring_id: str | None = None
    phase: str | None = None

    scenario_id: str | None = None