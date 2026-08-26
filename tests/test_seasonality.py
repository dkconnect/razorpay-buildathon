from data.generator.seasonality import (
    get_day_multiplier,
    get_rate_multiplier,
)

def test_seasonality_returns_positive_rates():
    for hour in range(24):
        assert get_rate_multiplier(hour) > 0


def test_evening_is_busier_than_night():
    assert (
        get_rate_multiplier(18)
        > get_rate_multiplier(3)
    )


def test_midday_is_busier_than_early_morning():
    assert (
        get_rate_multiplier(13)
        > get_rate_multiplier(7)
    )


def test_invalid_hour():
    # Hours outside 0-23 should not silently produce
    # an unexpected value.
    try:
        get_rate_multiplier(24)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for invalid hour")
    

def test_day_multipliers_are_positive():
    for day in range(7):
        assert get_day_multiplier(day) > 0


def test_weekend_is_busier_than_monday():
    assert (
        get_day_multiplier(5)
        > get_day_multiplier(0)
    )


def test_invalid_day():
    try:
        get_day_multiplier(7)
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected ValueError for invalid day"
        )