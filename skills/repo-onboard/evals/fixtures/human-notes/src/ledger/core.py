def add_cents(a: int, b: int) -> int:
    return a + b


def legacy_add(a, b):
    return add_cents(int(a), int(b))
