from datetime import datetime

from data.generator.stream import generate_stream


def test_generate_stream():
    start_time = datetime(2026, 1, 1, 12, 0, 0)

    transactions = generate_stream(
        start_time=start_time,
        num_transactions=5,
        interval_seconds=10,
    )

    assert len(transactions) == 5

    for tx in transactions:
        assert tx.is_fraud is False

    for i in range(1, len(transactions)):
        assert (
            transactions[i].timestamp
            > transactions[i - 1].timestamp
        )

    assert (
        transactions[1].timestamp
        - transactions[0].timestamp
    ).total_seconds() == 10