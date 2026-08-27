def validate_fraud_ground_truth(transactions):
# validate fraud label

    fraud_transactions = [
        transaction
        for transaction in transactions
        if transaction.is_fraud
    ]

    if not fraud_transactions:
        raise ValueError("No fraud transactions found")

    valid_phases = {"testing", "bust_out"}

    for transaction in fraud_transactions:
        if transaction.ring_id is None:
            raise ValueError(
                "Fraud transaction is missing ring_id"
            )

        if transaction.phase not in valid_phases:
            raise ValueError(
                f"Invalid fraud phase: {transaction.phase}"
            )

        if transaction.phase == "testing":
            if not 1 <= transaction.amount <= 50:
                raise ValueError(
                    "Testing transaction amount outside ₹1 - ₹50"
                )

        elif transaction.phase == "bust_out":
            if not 5000 <= transaction.amount <= 50000:
                raise ValueError(
                    "Bust-out transaction amount outside "
                    "₹5,000 - ₹50,000"
                )

    return True