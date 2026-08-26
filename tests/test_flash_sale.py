from collections import Counter
from datetime import datetime, timedelta

import numpy as np

from scenarios.flash_sale import (
    FLASH_SALE_DURATION_MINUTES,
    FLASH_SALE_START_MINUTE,
    generate_flash_sale,
)


def test_flash_sale_generation():
    transactions = generate_flash_sale()

    assert len(transactions) > 0

    for transaction in transactions:
        assert transaction.scenario_id == "flash_sale"
        assert transaction.is_fraud is False


def test_flash_sale_is_chronological():
    transactions = generate_flash_sale()

    timestamps = [
        transaction.timestamp
        for transaction in transactions
    ]

    assert timestamps == sorted(timestamps)


def test_flash_sale_has_expected_window():
    transactions = generate_flash_sale()

    start = datetime(2026, 1, 5, 0, 0, 0)

    sale_start = start + timedelta(
        minutes=FLASH_SALE_START_MINUTE
    )

    sale_end = sale_start + timedelta(
        minutes=FLASH_SALE_DURATION_MINUTES
    )

    sale_transactions = [
        transaction
        for transaction in transactions
        if sale_start <= transaction.timestamp < sale_end
    ]

    assert len(sale_transactions) > 0


def test_flash_sale_amounts_remain_legitimate():
    transactions = generate_flash_sale()

    amounts = np.array(
        [transaction.amount for transaction in transactions]
    )

    assert np.all(amounts > 0)
    assert np.median(amounts) < 5000


def test_flash_sale_is_reproducible():
    first = generate_flash_sale()
    second = generate_flash_sale()

    assert first == second

def test_flash_sale_volume_is_significantly_higher():
    transactions = generate_flash_sale()

    start = datetime(2026, 1, 5, 0, 0, 0)

    sale_start = start + timedelta(
        minutes=FLASH_SALE_START_MINUTE
    )

    sale_end = sale_start + timedelta(
        minutes=FLASH_SALE_DURATION_MINUTES
    )

    before_start = sale_start - timedelta(
        minutes=FLASH_SALE_DURATION_MINUTES
    )

    before_transactions = [
        transaction
        for transaction in transactions
        if before_start <= transaction.timestamp < sale_start
    ]

    sale_transactions = [
        transaction
        for transaction in transactions
        if sale_start <= transaction.timestamp < sale_end
    ]

    assert len(before_transactions) > 0
    assert len(sale_transactions) > 0

    volume_ratio = (
        len(sale_transactions)
        / len(before_transactions)
    )

    # The configured multiplier is 6x.
    # We allow randomness around that target.
    assert 3.5 < volume_ratio < 8.5


def test_flash_sale_does_not_create_fraud_labels():
    transactions = generate_flash_sale()

    fraud_transactions = [
        transaction
        for transaction in transactions
        if transaction.is_fraud
    ]

    assert fraud_transactions == []