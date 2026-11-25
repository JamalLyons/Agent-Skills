# Profiling tool categories

Pick what the project already uses; these are examples, not requirements. Confirm a tool exists before relying on it, and prefer sampling profilers on realistic workloads.

| Problem | Category | Examples |
| --- | --- | --- |
| CPU / latency in a process | Sampling or tracing profiler, flame graph | Python `cProfile`/`py-spy`, Node `--cpu-prof`/Chrome DevTools, Go `pprof`, JVM async-profiler/JFR, Rust/C `perf` + flame graphs, Instruments on macOS |
| Memory growth / leaks | Heap snapshots and allocation tracking, diffed over time | Python `tracemalloc`, Chrome heap snapshots, Go heap `pprof`, Valgrind massif/heaptrack, JVM heap dumps |
| Slow queries | Planner output with real timings; query counts per request | `EXPLAIN ANALYZE` (Postgres), `EXPLAIN ANALYZE`/slow log (MySQL), ORM query logging to spot N+1 |
| Web page / frontend | Performance panel, lab metrics, render and network waterfalls | Browser DevTools Performance, Lighthouse, React Profiler |
| Bundle size | Bundle analyzers and size budgets | `webpack-bundle-analyzer`, `source-map-explorer`, Vite/Rollup visualizers, `size-limit` |
| Tests / builds | Per-step timing and caching reports | test runner duration reports (`pytest --durations`), build tool profiles/traces (Gradle `--scan`, `tsc --extendedDiagnostics`, Bazel profile) |
| Microbenchmarks | Harnesses with warmup and statistics | `timeit`/`pytest-benchmark`, `hyperfine`, Go `testing.B`, JMH, Criterion, `tinybench` |

Measurement hygiene: use release/optimized builds, warm caches deliberately (or cold, consistently), fix input data and seeds, close noisy workloads, watch for thermal throttling and power modes, and run enough repetitions to see spread. Profilers add overhead; confirm improvements with the un-instrumented benchmark.
