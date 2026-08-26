from datetime import timedelta

import numpy as np
import random

from data.generator.amounts import generate_amounts
from data.generator.seasonality import get_expected_rate
from data.generator.transaction import generate_transaction

'''
I am using the same RNG for:
- arrival intervals
- transaction amounts

That gives us a single reproducible random stream for a generated merchant scenario.

And notice what we aren't doing:

is_fraud
ring_id
phase

This function produces legitimate traffic only.
'''

def generate_merchant_stream(
    start_time,
    duration_minutes,
    base_rate_per_minute=10.0,
    seed=None,
):
#Generate legitimate merchant traffic with time-varying Poisson arrivals.

    if duration_minutes <= 0:
        raise ValueError("duration_minutes must be positive")

    rng = np.random.default_rng(seed)
    identity_rng = random.Random(seed)

    transactions = []
    current_time = start_time
    end_time = start_time + timedelta(minutes=duration_minutes)

    while current_time < end_time:
        rate = get_expected_rate(
            current_time,
            base_rate_per_minute=base_rate_per_minute,
        )

        rate_per_second = rate / 60.0

        interval_seconds = rng.exponential(
            scale=1.0 / rate_per_second
        )

        current_time += timedelta(
            seconds=float(interval_seconds)
        )

        if current_time >= end_time:
            break

        amount = rng.lognormal(
            mean=7.5,
            sigma=0.8,
        )

        transactions.append(
            generate_transaction(
                timestamp=current_time,
                amount=round(float(amount), 2),
                rng=identity_rng,
            )
        )

    return transactions