---
name: perf-investigation
description: Diagnose performance problems by measurement, then make bounded, verified optimizations when requested. Use when something is slow, uses too much memory or CPU, a query/page/build/test suite is slow, a perf regression appeared, or the user wants to optimize with measurements. A diagnosis-only request does not authorize edits, production load tests, or publication. Do not use for functional bugs (bug-investigation) or speculative refactors without a measured problem.
---

# Performance investigation

Replace intuition with measurement before changing code. Use the host's actual tools and the repository's conventions; no particular profiler, agent, or delegation API is required.

## Define the problem

- State the metric (latency, throughput, CPU, peak/retained memory, bundle bytes, query time, test/build duration), the workload, the environment, and the target or budget. If no target exists, say so and use "measurably better than baseline without regressions".
- Resolve scope: diagnose, or diagnose and fix. Preserve dirty/index/untracked work and record the revision measured. Inspect scripts before running them.
- Measure locally or in an isolated environment with synthetic or representative data. A perf request does not authorize production load tests, traffic replay against live services, credential changes, deployment, or publishing.

## Establish a baseline

Build a repeatable benchmark or reproduction that isolates the slow path: fixed inputs and seeds, warmup, several runs. Report median and p95 (or min/max) with spread, not a single number. Check how the cost scales with input size; a doubling test often separates linear from quadratic behavior.

Note noise sources and control what you can: debug vs optimized builds, cold vs warm caches, JIT warmup, background load, thermal throttling or power mode, network variance. A difference smaller than run-to-run spread is not an improvement.

## Profile and form hypotheses

Profile before editing. Choose a tool category that fits the ecosystem and metric — CPU sampling profilers and flame graphs, heap snapshots or allocation tracking, `EXPLAIN ANALYZE` and query counts, bundle analyzers, per-step test/build timing. See `references/profiling-tools.md` for examples; use what is installed and say when a tool is unavailable.

Keep competing hypotheses (for example: algorithmic complexity, I/O or N+1 queries, contention, allocation/GC pressure, caching, configuration). For each, pick a measurement that would discriminate it from the others — time phases separately, vary input size, count calls. Treat a reported cause ("it's the database") as a hypothesis to test, not a fact. Keep observations separate from inference.

## Fix within scope

For diagnosis-only work, stop after the evidenced explanation and a proposed change with its expected effect; leave project files unchanged. When a fix is authorized:

1. Change one thing at a time, targeting the measured hotspot. Prefer the simplest change that removes the cost (better algorithm or data structure, batching, avoiding repeated work) over broad rewrites or new caches.
2. Re-measure against the baseline under identical conditions. Keep only changes with an improvement beyond noise; revert ones that do not help, and record them as rejected.
3. Guard correctness: run existing tests and the contract checks before and after. Do not weaken tests, change outputs, or drop edge cases for speed.
4. Add a performance regression check where the repo supports one — benchmark test, budget or complexity assertion, CI size limit — without making the suite flaky on slow machines. If none fits, say so.
5. Remove investigation-only instrumentation and temporary files.

## Stop and report

Bound experiments to the uncertainty. If the next step needs production access, realistic data you lack, or a product trade-off, name the blocker and the most valuable next measurement.

Report: the metric and workload, measurement method (runs, warmup, environment), baseline vs after numbers with spread, the evidenced cause, what was tried and rejected, remaining hotspots, checks run, and limits — for example, measured locally on synthetic data, not in production. Push, post, or open a PR only when authorized.
