from pathlib import Path

from data.io import load_transactions


NORMAL_PATH = Path("data/generated/normal_day.json")
FLASH_SALE_PATH = Path("data/generated/flash_sale.json")


def test_normal_day_dataset_exists():
    assert NORMAL_PATH.exists()


def test_flash_sale_dataset_exists():
    assert FLASH_SALE_PATH.exists()


def test_normal_day_dataset_is_valid():
    transactions = load_transactions(NORMAL_PATH)

    assert len(transactions) > 0

    assert all(
        transaction.is_fraud is False
        for transaction in transactions
    )

    assert all(
        transaction.scenario_id == "normal_day"
        for transaction in transactions
    )


def test_flash_sale_dataset_is_valid():
    transactions = load_transactions(FLASH_SALE_PATH)

    assert len(transactions) > 0

    assert all(
        transaction.is_fraud is False
        for transaction in transactions
    )

    assert all(
        transaction.scenario_id == "flash_sale"
        for transaction in transactions
    )