import random
import uuid

from data.schema import Transaction


def generate_transaction(timestamp, amount=None):
#generating on legitimate transac tion

    if amount is None:
        amount = random.lognormvariate(7.0, 0.8)

    return Transaction(
        transaction_id=str(uuid.uuid4()),
        timestamp=timestamp,
        amount=round(amount, 2),
        customer_id=f"customer_{random.randint(1, 1000)}",
        device_id=f"device_{random.randint(1, 800)}",
        ip_subnet=f"10.0.{random.randint(0, 255)}.0/24",
        card_bin=f"{random.randint(400000, 499999)}",
        is_fraud=False,
        ring_id=None,
        phase=None,
        scenario_id=None,
    )