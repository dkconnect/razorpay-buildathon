from datetime import datetime
from pathlib import Path

from data.generator.ground_truth import (
    validate_fraud_ground_truth,
)
from data.io import save_transactions
from scenarios.mixed_fraud import (
    generate_mixed_fraud_scenario,
)


OUTPUT_DIR = Path("data/generated")


def main():
    start_time = datetime(2026, 1, 5, 12, 0, 0)
    seed = 42

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    transactions = generate_mixed_fraud_scenario(
        start_time=start_time,
        seed=seed,
    )

    validate_fraud_ground_truth(
        transactions
    )

    output_path = (
        OUTPUT_DIR / "mixed_fraud.json"
    )

    save_transactions(
        transactions,
        output_path,
    )

    fraud = [
        transaction
        for transaction in transactions
        if transaction.is_fraud
    ]

    testing = [
        transaction
        for transaction in fraud
        if transaction.phase == "testing"
    ]

    bust_out = [
        transaction
        for transaction in fraud
        if transaction.phase == "bust_out"
    ]

    print("Day 2 dataset generated")
    print("-----------------------")
    print(f"total:     {len(transactions)}")
    print(f"legitimate: {len(transactions) - len(fraud)}")
    print(f"fraud:     {len(fraud)}")
    print(f"testing:   {len(testing)}")
    print(f"bust_out:  {len(bust_out)}")
    print(f"seed:      {seed}")
    print(f"output:    {output_path}")

if __name__ == "__main__":
    main()