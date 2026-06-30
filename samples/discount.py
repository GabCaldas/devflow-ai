def apply_discount(price, percent):
    return price - price * percent / 100


def total_with_tax(price, tax):
    return price + price * tax
