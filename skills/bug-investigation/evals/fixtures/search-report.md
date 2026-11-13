# Search API report

The API contract accepts a nonnegative integer `limit`, or `None` for no limit.
The result must contain at most `limit` matching products in input order. The
client uses zero to request no results while displaying a disabled search view.

Observed locally: searching for `blue` with limit `0` returned all three products.
The same request with limit `2` returned the first two products. A colleague
suggested this might be a cached response; this fixture contains no network or
cache service. Existing tests can run with `python3 -m unittest -v` from the
directory containing `catalog.py` and `test_catalog.py`. No third-party packages
are required. The attached files are a synthetic pinned reproduction fixture,
not access to a live project or service.
