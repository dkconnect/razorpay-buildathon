from datetime import timedelta

from config.scenario import ScenarioConfig
from data.generator.merchant import generate_merchant_stream


FLASH_SALE_CONFIG = ScenarioConfig(
    name="flash_sale",
    duration_minutes=24 * 60,
    base_rate_per_minute=10.0,
    seed=43,
)

FLASH_SALE_START_MINUTE = 12 * 60
FLASH_SALE_DURATION_MINUTES = 120
FLASH_SALE_MULTIPLIER = 6.0


def generate_flash_sale():
# creates a legitimate merchant day 

    start_time = __import__("datetime").datetime(
        2026,
        1,
        5,
        0,
        0,
        0,
    )

    before_sale = generate_merchant_stream(
        start_time=start_time,
        duration_minutes=FLASH_SALE_START_MINUTE,
        base_rate_per_minute=FLASH_SALE_CONFIG.base_rate_per_minute,
        seed=FLASH_SALE_CONFIG.seed,
    )

    sale_start = start_time + timedelta(
        minutes=FLASH_SALE_START_MINUTE
    )

    during_sale = generate_merchant_stream(
        start_time=sale_start,
        duration_minutes=FLASH_SALE_DURATION_MINUTES,
        base_rate_per_minute=(
            FLASH_SALE_CONFIG.base_rate_per_minute
            * FLASH_SALE_MULTIPLIER
        ),
        seed=FLASH_SALE_CONFIG.seed + 1,
    )

    after_sale_start = sale_start + timedelta(
        minutes=FLASH_SALE_DURATION_MINUTES
    )

    after_sale = generate_merchant_stream(
        start_time=after_sale_start,
        duration_minutes=(
            FLASH_SALE_CONFIG.duration_minutes
            - FLASH_SALE_START_MINUTE
            - FLASH_SALE_DURATION_MINUTES
        ),
        base_rate_per_minute=FLASH_SALE_CONFIG.base_rate_per_minute,
        seed=FLASH_SALE_CONFIG.seed + 2,
    )

    transactions = before_sale + during_sale + after_sale

    transactions.sort(
        key=lambda transaction: transaction.timestamp
    )

    for transaction in transactions:
        transaction.scenario_id = FLASH_SALE_CONFIG.name

    return transactions