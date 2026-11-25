"""Repeatable benchmark for orders.build_report. Run: python3 bench_orders.py [--size N]."""
import argparse
import random
import statistics
import time

from orders import FakeDB, build_report, load_orders


def make_data(size, seed=1234):
    rng = random.Random(seed)
    customers = [f"c{i}" for i in range(size // 4 or 1)]
    orders = [
        {"id": f"o{i}", "customer_id": rng.choice(customers), "amount": rng.randint(1, 500)}
        for i in range(size)
    ]
    vip_ids = customers[: len(customers) // 2 or 1]
    return orders, customers, vip_ids


def timed(fn, runs, warmup):
    for _ in range(warmup):
        fn()
    samples = []
    for _ in range(runs):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    return samples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=8000)
    parser.add_argument("--runs", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2)
    args = parser.parse_args()
    orders, customers, vip_ids = make_data(args.size)
    db = FakeDB(orders)
    phases = {
        "load_orders": lambda: load_orders(db, customers),
        "build_report": lambda: build_report(orders, vip_ids),
    }
    for name, fn in phases.items():
        samples = sorted(timed(fn, args.runs, args.warmup))
        p95 = samples[min(len(samples) - 1, round(0.95 * (len(samples) - 1)))]
        print(
            f"{name}: size={args.size} runs={args.runs} median={statistics.median(samples) * 1000:.2f}ms "
            f"p95={p95 * 1000:.2f}ms min={samples[0] * 1000:.2f}ms max={samples[-1] * 1000:.2f}ms"
        )


if __name__ == "__main__":
    main()
