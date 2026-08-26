from datetime import timedelta

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