---
name: codebase-design
license: MIT
description: Shared vocabulary for designing deep modules. Use when the user wants to design or improve a module's interface, find deepening opportunities, decide where a seam goes, make code more testable or AI-navigable, or when another skill needs the deep-module vocabulary.
---

# Codebase Design

Consider **deep modules**: useful behaviour behind a manageable interface, placed at a clean seam, testable through that interface. The aim is leverage for callers, locality for maintainers, and testability. Deepening is one design option, not a reason to merge modules that already protect useful invariants, ownership, or isolation.

## Glossary

Use these terms consistently for architectural reasoning. Preserve established domain terms, API names, and code identifiers; this vocabulary is not a reason to rename working code.

**Module**: anything with an interface and an implementation. Deliberately scale-agnostic: a function, class, package, or tier-spanning slice. Use the repository's more specific term—such as component or service—when it conveys established meaning.

**Interface**: everything a caller must know to use the module correctly: the type signature, but also invariants, ordering constraints, error modes, required configuration, and performance characteristics. An established API name stays an API name; clarify its broader behavioral contract when that matters.

**Implementation**: what's inside a module, its body of code. Distinct from **Adapter**: a thing can be a small adapter with a large implementation (a Postgres repo) or a large adapter with a small implementation (an in-memory fake). Reach for "adapter" when the seam is the topic; "implementation" otherwise.

**Depth**: leverage at the interface. The amount of behaviour a caller (or test) can exercise per unit of interface they have to learn. A module is **deep** when a large amount of behaviour sits behind a small interface, **shallow** when the interface is nearly as complex as the implementation.

**Seam** _(Michael Feathers)_: a place where you can alter behaviour without editing in that place; the *location* at which a module's interface lives. Where to put the seam is its own design decision, distinct from what goes behind it. Preserve established boundary terminology and distinguish a test seam from a domain, ownership, process, or security boundary.

**Adapter**: a concrete thing that satisfies an interface at a seam. Describes *role* (what slot it fills), not substance (what's inside).

**Leverage**: what callers get from depth. More capability per unit of interface they learn. One implementation pays back across N call sites and M tests.

**Locality**: what maintainers get from depth. Change, bugs, knowledge, and verification concentrate in one place rather than spreading across callers. Fix once, fixed everywhere.

## Deep vs shallow

**Deep module** = small interface + lots of implementation:

```
┌─────────────────────┐
│   Small Interface   │  ← Few methods, simple params
├─────────────────────┤
│                     │
│  Deep Implementation│  ← Complex logic hidden
│                     │
└─────────────────────┘
```

**Potentially shallow module** = large interface + little implementation (investigate):

```
┌─────────────────────────────────┐
│       Large Interface           │  ← Many methods, complex params
├─────────────────────────────────┤
│  Thin Implementation            │  ← Just passes through
└─────────────────────────────────┘
```

When designing an interface, ask:

- Can I reduce the number of methods?
- Can I simplify the parameters?
- Can I hide more complexity inside?
- What useful invariant, ownership, or isolation would consolidation remove?

## Principles

- **Depth is a property of the interface, not the implementation.** A deep module can be internally composed of small, mockable, swappable parts; they just aren't part of the interface. A module can have **internal seams** (private to its implementation, used by its own tests) as well as the **external seam** at its interface.
- **The deletion test is a heuristic.** Imagine removing the module. Complexity returning across callers suggests it earns its keep. Little code can still enforce authorization, lifecycle, or compatibility; account for that contract before calling it a pass-through.
- **Prefer tests at the relevant interface.** Callers and tests usually cross the same seam. Investigate tests reaching through it, but retain lower-level checks when they directly verify a meaningful invariant or failure mode that broader tests would obscure.
- **Variation can justify a seam; adapter count does not decide it.** Two real implementations are useful evidence. One adapter may still isolate an external system, enforce security or ownership, or protect a changing contract. Do not invent a second adapter merely to justify an abstraction.

## Designing for testability

Good interfaces make testing natural:

1. **Accept dependencies, don't create them.**

   ```typescript
   // Testable
   function processOrder(order, paymentGateway) {}

   // Hard to test
   function processOrder(order) {
     const gateway = new StripeGateway();
   }
   ```

2. **Prefer explicit results and controlled side effects.** Pure calculations are easy to exercise; persistence and other effects can be the required behavior, so expose and verify their contract rather than removing them for testability.

   ```typescript
   // Testable
   function calculateDiscount(cart): Discount {}

   // Hard to test
   function applyDiscount(cart): void {
     cart.total -= discount;
   }
   ```

3. **Manageable surface area.** Fewer concepts and parameters can simplify callers and setup. Method count does not determine test count: a single configurable operation may have many interacting states. Preserve explicit operations when they make valid behavior easier to understand.

Leave the structure alone when there is no demonstrated change friction, when a thin layer protects a useful contract, or when consolidation would couple independent ownership, release cycles, or trust boundaries. Compare the proposed improvement with that baseline before recommending a refactor.

## Relationships

- A **Module** presents an **Interface** to each relevant caller; distinct roles can legitimately have distinct surfaces.
- **Depth** is a property of a **Module**, measured against its **Interface**.
- A **Seam** is where a **Module**'s **Interface** lives.
- An **Adapter** sits at a **Seam** and satisfies the **Interface**.
- **Depth** produces **Leverage** for callers and **Locality** for maintainers.

## Rejected framings

- **Depth as ratio of implementation-lines to interface-lines** (Ousterhout): rewards padding the implementation. We use depth-as-leverage instead.
- **"Interface" as the TypeScript `interface` keyword or a class's public methods**: too narrow: interface here includes every fact a caller must know.
- **Terminology as a rename mandate**: use the vocabulary to clarify reasoning, not to replace established API, component, service, or boundary names.

## Going deeper

- **Deepening a cluster given its dependencies**, see [DEEPENING.md](DEEPENING.md): dependency categories, seam discipline, and replace-don't-layer testing.
- **Exploring alternative interfaces**, see [DESIGN-IT-TWICE.md](DESIGN-IT-TWICE.md): design the interface several radically different ways, using permitted parallel subagents when available, then compare on depth, locality, and seam placement.
