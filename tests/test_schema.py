from datetime import datetime

from data.schema import Transaction


def test_transaction_creation():
    tx = Transaction(
        transaction_id="tx_001",
        timestamp=datetime.now(),
        amount=1000.0,
        customer_id="customer_001",
        device_id="device_001",
        ip_subnet="192.168.1.0/24",
        card_bin="411111",
    )

    assert tx.transaction_id == "tx_001"
    assert tx.amount == 1000.0
    assert tx.is_fraud is False
    assert tx.ring_id is None
    assert tx.phase is None