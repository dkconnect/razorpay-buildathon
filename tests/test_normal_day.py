from scenarios.normal_day import generate_normal_day


def test_normal_day_generation():
    transactions = generate_normal_day()

    assert len(transactions) > 0

    for transaction in transactions:
        assert transaction.scenario_id == "normal_day"
        assert transaction.is_fraud is False


def test_normal_day_is_reproducible():
    first = generate_normal_day()
    second = generate_normal_day()

    assert first == second


def test_normal_day_is_chronological():
    transactions = generate_normal_day()

    timestamps = [
        transaction.timestamp
        for transaction in transactions
    ]

    assert timestamps == sorted(timestamps)