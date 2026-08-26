from datetime import timedelta

from data.generator.arrivals import generate_interarrival_times
from data.generator.transaction import generate_transaction


def generate_stream(start_time, num_transactions, interval_seconds=10):
#generating a stream of legitimate transaction 

    transactions = []

    for i in range(num_transactions):
        timestamp = start_time + timedelta(
            seconds=i * interval_seconds
        )

        transactions.append(
            generate_transaction(timestamp)
        )

    return transactions

def generate_poisson_stream(
    start_time,
    num_transactions,
    rate_per_minute,
    seed=None,
):

#Generates legitimate transactions using Poisson arrivals and a lognormal amount distribution.

    import numpy as np

    interarrival_times = generate_interarrival_times(
        num_transactions=num_transactions,
        rate_per_minute=rate_per_minute,
        seed=seed,
    )

    rng = np.random.default_rng(seed)

    transactions = []
    current_time = start_time

    for interval in interarrival_times:
        current_time += timedelta(seconds=float(interval))

        amount = rng.lognormal(
            mean=7.5,
            sigma=0.8,
        )

        transactions.append(
            generate_transaction(
                current_time,
                amount=round(float(amount), 2),
            )
        )

    return transactions