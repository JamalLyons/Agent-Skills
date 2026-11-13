---
name: tdd
license: MIT
description: Test-driven development. Use when the user wants to build features or fix bugs test-first, mentions "red-green-refactor", or wants integration tests.
---

# Test-Driven Development

TDD is the red → green loop. This skill is the reference that makes that loop produce tests worth keeping: what a good test is, where tests go, the anti-patterns, and the rules of the loop. Every section applies on every cycle: consult them before and during the loop, not after.

When exploring the codebase, read `GLOSSARY.md` (if it exists) so test names and interface vocabulary match the project's domain language, and respect ADRs in the area you're touching.

## What a good test is

Tests verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't. A good test reads like a specification: "user can checkout with valid cart" tells you exactly what capability exists, and it survives refactors because it doesn't care about internal structure.

See [tests.md](tests.md) for examples and [mocking.md](mocking.md) for mocking guidelines.

## Seams: where tests go

A **seam** is the interface where a test observes the chosen behavioral contract. Prefer the same interface callers use over reaching into incidental internals.

Identify the public interfaces under test from the user's request, existing tests, and repository conventions. State what the chosen seams catch and miss. Ask only when a consequential interface or behavior decision remains unresolved; an existing agreement does not need reconfirmation.

Choose assertions by that contract. Database constraints, migration compatibility, durable writes, externally required ordering, and exactly-once delivery can require persistence checks or boundary call/count assertions. Use them when they observe the promised behavior; avoid asserting private orchestration merely because it is convenient to spy on.

When the shape of that interface is itself in question (how deep the module is, where the seam belongs, what the interface should expose), read [codebase-design](../codebase-design/SKILL.md) for the vocabulary. It is the shared source of the module, interface, depth, seam, adapter, leverage and locality terms, and it is a reference to consult, not a session to run.

## Anti-patterns

- **Implementation-coupled**: replaces internal collaborators or inspects private state without testing a promised behavior. A database query can be a side channel for an application test, but the right observation for a persistence or migration contract. The tell: the test breaks when you refactor but its behavioral contract has not changed.
- **Tautological**: the assertion recomputes the expected value the way the code does (`expect(add(a, b)).toBe(a + b)`, a snapshot derived by hand the same way, a constant asserted equal to itself), so it passes by construction and can never disagree with the code. Expected values must come from an independent source of truth: a known-good literal, a worked example, the spec.
- **Horizontal slicing**: writing all tests first, then all implementation. Bulk tests verify _imagined_ behavior: you test the _shape_ of things rather than user-facing behavior, the tests go insensitive to real changes, and you commit to test structure before understanding the implementation. Work in **vertical slices** instead: one test → one implementation → repeat, each test a **tracer bullet** that responds to what the last cycle taught you.

## Rules of the loop

- **Red before green.** Write the failing test first, then only enough code to pass it. Don't anticipate future tests or add speculative features.
- **One slice at a time.** One seam, one test, one minimal implementation per cycle.
- **Refactor after green.** Simplify when it improves the current slice, keeping behavior and tests green. Use [code-review](../code-review/SKILL.md) when a separate review is requested; it is not a prerequisite for each cycle.
- **Check the failure reason.** Run each new test and confirm it fails for the missing behavior before implementing. If the test runner cannot run, report that limitation instead of claiming a red or green result.

## Finish the change

Run relevant existing regressions and the checks required by the repository for the changed behavior. Select meaningful success and failure paths; do not require the full suite after every slice. Summarize what behavior is covered, which checks actually ran and their outcomes, and any untested seams or unavailable checks. A passing mock test does not establish real adapter or persistence compatibility.
