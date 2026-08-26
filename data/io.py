import json
from dataclasses import asdict
from pathlib import Path

from data.schema import Transaction


def save_transactions(transactions, path):

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    records = []

    for transaction in transactions:
        record = asdict(transaction)

        record["timestamp"] = transaction.timestamp.isoformat()

        records.append(record)

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            records,
            file,
            indent=2,
        )


def load_transactions(path):

    path = Path(path)

    with path.open("r", encoding="utf-8") as file:
        records = json.load(file)

    transactions = []

    for record in records:
        record["timestamp"] = __import__(
            "datetime"
        ).datetime.fromisoformat(
            record["timestamp"]
        )

        transactions.append(
            Transaction(**record)
        )

    return transactions