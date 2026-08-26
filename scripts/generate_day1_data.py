from pathlib import Path

from data.io import save_transactions
from scenarios.flash_sale import generate_flash_sale
from scenarios.normal_day import generate_normal_day


OUTPUT_DIR = Path("data/generated")


def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("Generating normal-day dataset...")
    normal_day = generate_normal_day()

    normal_path = OUTPUT_DIR / "normal_day.json"

    save_transactions(
        normal_day,
        normal_path,
    )

    print(
        f"Saved {len(normal_day)} transactions "
        f"to {normal_path}"
    )

    print("Generating flash-sale dataset...")
    flash_sale = generate_flash_sale()

    flash_sale_path = OUTPUT_DIR / "flash_sale.json"

    save_transactions(
        flash_sale,
        flash_sale_path,
    )

    print(
        f"Saved {len(flash_sale)} transactions "
        f"to {flash_sale_path}"
    )


if __name__ == "__main__":
    main()