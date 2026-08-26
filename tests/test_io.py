from datetime import datetime

from data.io import load_transactions, save_transactions
from data.schema import Transaction


def test_save_and_load_transactions(tmp_path):
    transactions = [
        Transaction(
            transaction_id="tx_test_001",
            timestamp=datetime(2026, 1, 5, 12, 0, 0),
            amount=1500.50,
            customer_id="customer_1",
            device_id="device_1",
            ip_subnet="10.0.1.0/24",
            card_bin="411111",
            is_fraud=False,
            ring_id=None,
            phase=None,
            scenario_id="normal_day",
        )
    ]

    path = tmp_path / "transactions.json"

    save_transactions(
        transactions,
        path,
    )

    loaded = load_transactions(path)

    assert loaded == transactions


def test_save_creates_parent_directory(tmp_path):
    transactions = []

    path = (
        tmp_path
        / "nested"
        / "directory"
        / "data.json"
    )

    save_transactions(
        transactions,
        path,
    )

    assert path.exists()


def test_empty_dataset_round_trip(tmp_path):
    path = tmp_path / "empty.json"

    save_transactions([], path)

    loaded = load_transactions(path)

    assert loaded == []