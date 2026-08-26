from datetime import datetime

from data.generator.transaction import generate_transaction


def test_generate_legitimate_transaction():
    timestamp = datetime(2026, 1, 1, 12, 0, 0)

    tx = generate_transaction(timestamp)

    assert tx.transaction_id
    assert tx.timestamp == timestamp
    assert tx.amount > 0

    assert tx.customer_id.startswith("customer_")
    assert tx.device_id.startswith("device_")
    assert tx.ip_subnet.startswith("10.0.")
    assert len(tx.card_bin) == 6

    assert tx.is_fraud is False
    assert tx.ring_id is None
    assert tx.phase is None