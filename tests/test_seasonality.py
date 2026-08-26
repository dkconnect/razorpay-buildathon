from data.generator.seasonality import get_rate_multiplier


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