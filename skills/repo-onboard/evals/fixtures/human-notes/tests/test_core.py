from ledger.core import add_cents, legacy_add


def test_add_cents():
    assert add_cents(150, 250) == 400


def test_legacy_add():
    assert legacy_add("1", 2) == 3
