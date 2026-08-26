def get_rate_multiplier(hour):
# will return the relative transaction rate multiplier for an hour

    if not 0 <= hour <= 23:
        raise ValueError("hour should be between 0 and 23")

    if 0 <= hour < 6:
        return 0.25
    if 6 <= hour < 9:
        return 0.50
    if 9 <= hour < 12:
        return 0.80
    if 12 <= hour < 16:
        return 1.00
    if 16 <= hour < 20:
        return 1.50
    if 20 <= hour < 23:
        return 1.20

    return 0.70