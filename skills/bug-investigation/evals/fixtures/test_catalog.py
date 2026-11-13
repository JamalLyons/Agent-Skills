import unittest

from catalog import search


PRODUCTS = [
    {"id": "p1", "name": "Blue notebook"},
    {"id": "p2", "name": "Blue pencil"},
    {"id": "p3", "name": "Blue folder"},
]


class SearchTests(unittest.TestCase):
    def test_positive_limit(self):
        self.assertEqual([p["id"] for p in search(PRODUCTS, "blue", 2)], ["p1", "p2"])

    def test_default_preserves_order_and_all_matches(self):
        self.assertEqual(search(PRODUCTS, "BLUE"), PRODUCTS)

    def test_negative_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            search(PRODUCTS, "blue", -1)


if __name__ == "__main__":
    unittest.main()
