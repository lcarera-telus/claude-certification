SETTINGS = {
    "tax_rate": 0.21,
    "currency": "USD",
    "discount_cap": 25,
    "verbose": False,
}


def get(key, default=None):
    return SETTINGS.get(key, default)
