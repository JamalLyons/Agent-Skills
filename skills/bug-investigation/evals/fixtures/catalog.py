"""Small in-memory catalog used by the local search API."""


def search(products, query, limit=None):
    """Return matching products in input order; None means no result limit."""
    if limit is not None and limit < 0:
        raise ValueError("limit must not be negative")
    matches = [product for product in products if query.casefold() in product["name"].casefold()]
    return matches[:limit] if limit else matches
