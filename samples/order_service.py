"""Synthetic change used to validate the DevFlow AI review workflow."""


def calculate_order_total(items: list[dict], discount_percent: float) -> float:
    subtotal = sum(item["price"] * item["quantity"] for item in items)
    return subtotal * (1 - discount_percent / 100)
