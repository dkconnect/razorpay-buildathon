import random

from data.schema import Transaction

def generate_transaction(timestamp, amount=None, rng=None):
#generating on legitimate transac tion

    if rng is None:
        rng = random.Random()

    if amount is None:
        amount = rng.lognormvariate(7.0, 0.8)

    return Transaction(
        transaction_id=f"tx_{rng.getrandbits(64):016x}",
        timestamp=timestamp,
        amount=round(amount, 2),
        customer_id=f"customer_{rng.randint(1, 1000)}",
        device_id=f"device_{rng.randint(1, 800)}",
        ip_subnet=f"10.0.{rng.randint(0, 255)}.0/24",
        card_bin=f"{rng.randint(400000, 499999)}",
        is_fraud=False,
        ring_id=None,
        phase=None,
        scenario_id=None,
    )