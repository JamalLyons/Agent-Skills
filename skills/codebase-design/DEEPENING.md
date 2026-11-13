# Deepening

How to deepen a cluster of shallow modules safely, given its dependencies. Assumes the vocabulary in [SKILL.md](SKILL.md): **module**, **interface**, **seam**, **adapter**.

## Dependency categories

When assessing a candidate for deepening, classify its dependencies. The category informs testing and migration; it does not establish that consolidation is worthwhile.

### 1. In-process

Pure computation, in-memory state, no I/O. Consolidation may be straightforward, with direct tests through the resulting interface. First check whether existing modules express independent invariants, ownership, or reusable concepts; in-process code is not automatically better merged. An adapter is unnecessary unless it serves an actual contract.

### 2. Local-substitutable

Dependencies that have local test stand-ins (PGLite for Postgres, in-memory filesystem). A stand-in can make interface tests practical, but first identify behavior it cannot establish, such as production transaction or filesystem semantics. Keep the seam internal when callers do not need it; use real-system checks where compatibility is part of the contract.

### 3. Remote but owned (Ports & Adapters)

Your own services across a network boundary (microservices, internal APIs). Define a **port** (interface) at the seam. The deep module owns the logic; the transport is injected as an **adapter**. Tests use an in-memory adapter. Production uses an HTTP/gRPC/queue adapter.

Recommendation shape: *"Define a port at the seam, implement an HTTP adapter for production and an in-memory adapter for testing, so the logic sits in one deep module even though it's deployed across a network."*

### 4. True external (Mock)

Third-party services (Stripe, Twilio, etc.) you don't control. The deepened module takes the external dependency as an injected port; tests provide a mock adapter.

## Seam discipline

- **Justify the seam by its contract.** Real variation is evidence, not an adapter-count rule. One adapter can protect trust, ownership, lifecycle, or compatibility. Two adapters do not make an otherwise unnecessary abstraction useful; do not manufacture a test adapter solely to satisfy a count.
- **Internal seams vs external seams.** A deep module can have internal seams (private to its implementation, used by its own tests) as well as the external seam at its interface. Don't expose internal seams through the interface just because tests use them.

## Testing strategy: replace, don't layer

- Replace tests coupled to removed internals only after new interface tests preserve their meaningful behavioral coverage. Keep independent regression coverage; do not delete tests merely because they are unit tests.
- Write new tests at the deepened module's interface. The **interface is the test surface**.
- Tests assert on observable outcomes through the interface, not internal state.
- Tests should usually survive internal refactors. When a test changes, inspect whether meaningful behavior or a deliberately tested invariant changed before labeling it implementation-coupled. Keep independent failure-path and regression coverage even when the new interface is harder to exercise precisely.

Before recommending consolidation, identify an actual costly change or defect, the contract that must survive, and a bounded migration path. Keep existing structure when the evidence of benefit is weak or the migration would erase useful isolation. A smaller interface is not itself evidence of lower overall complexity.
