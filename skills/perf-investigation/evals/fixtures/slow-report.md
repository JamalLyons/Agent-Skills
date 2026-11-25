# Slow VIP report

The nightly VIP order report has become slow as order volume grew. Last month it
finished in seconds; it now takes minutes on production-sized data. A teammate
wrote: "It's obviously the database — we should add an index or a cache in front
of `load_orders`."

Contract: `build_report(orders, vip_ids)` returns VIP orders in input order with a
per-customer running total; `vip_ids` may be any iterable. `load_orders` must stay
a single batched query.

This fixture is synthetic. `orders.py` uses an in-memory `FakeDB`; there is no real
database, cache, or production environment. From the directory containing these
files, `python3 bench_orders.py --size N` times both phases (see `--help`), and
`python3 -m unittest check_orders -v` runs the correctness checks. No third-party
packages are required.
