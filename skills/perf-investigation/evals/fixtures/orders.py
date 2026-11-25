"""Synthetic order-report module for a performance investigation fixture."""


def load_orders(db, customer_ids):
    """Fetch orders for the given customers with one batched query."""
    return db.query_orders(customer_ids)


def build_report(orders, vip_ids):
    """Return VIP orders in input order, each with a running total per customer."""
    vip_list = list(vip_ids)
    totals = {}
    report = []
    for order in orders:
        if order["customer_id"] in vip_list:
            customer = order["customer_id"]
            totals[customer] = totals.get(customer, 0) + order["amount"]
            report.append({**order, "running_total": totals[customer]})
    return report


class FakeDB:
    """In-memory stand-in for the database; one call per batch, no network."""

    def __init__(self, orders):
        self._orders = orders
        self.calls = 0

    def query_orders(self, customer_ids):
        self.calls += 1
        wanted = set(customer_ids)
        return [o for o in self._orders if o["customer_id"] in wanted]
