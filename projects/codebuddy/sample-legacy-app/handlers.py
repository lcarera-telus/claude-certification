import config
import legacy_pricing
import utils


def handle_quote(payload):
    total = legacy_pricing.calc(
        payload.get("items", []),
        payload.get("country", "US"),
        payload.get("discount", 0),
        payload.get("flagged", False),
    )
    return {
        "total": utils.round_money(total),
        "currency": config.get("currency", "USD"),
        "slug": utils.slugify(payload.get("name", "quote")),
    }


def handle_receipt(payload):
    lines = []
    for item in payload.get("items", []):
        lines.append(
            {
                "label": utils.slugify(item.get("label", "item")),
                "amount": utils.round_money(item.get("price", 0) * item.get("qty", 1)),
            }
        )
    return {"lines": lines, "count": len(lines)}


def handle_summary(payload):
    cap = config.get("discount_cap", 0)
    d = payload.get("discount", 0)
    if d > cap:
        d = cap
    return {
        "name": utils.slugify(payload.get("name", "summary")),
        "discount": d,
        "capped": d == cap,
    }
