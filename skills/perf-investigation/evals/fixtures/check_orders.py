"""Correctness checks for orders.py. Run: python3 -m unittest check_orders -v."""
import unittest

from orders import FakeDB, build_report, load_orders

ORDERS = [
    {"id": "o1", "customer_id": "a", "amount": 10},
    {"id": "o2", "customer_id": "b", "amount": 5},
    {"id": "o3", "customer_id": "a", "amount": 7},
    {"id": "o4", "customer_id": "c", "amount": 1},
]


class ReportChecks(unittest.TestCase):
    def test_filters_vips_in_input_order_with_running_totals(self):
        report = build_report(ORDERS, ["a", "c"])
        self.assertEqual([r["id"] for r in report], ["o1", "o3", "o4"])
        self.assertEqual([r["running_total"] for r in report], [10, 17, 1])

    def test_accepts_any_iterable_of_vip_ids(self):
        self.assertEqual(len(build_report(ORDERS, iter(["b"]))), 1)

    def test_load_orders_is_one_batched_query(self):
        db = FakeDB(ORDERS)
        self.assertEqual(len(load_orders(db, ["a", "b"])), 3)
        self.assertEqual(db.calls, 1)


if __name__ == "__main__":
    unittest.main()
