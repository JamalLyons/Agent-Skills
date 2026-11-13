---
name: domain-modeling
license: MIT
description: Build and sharpen a project's domain model. Use when discussing codebase terminology, writing or editing a GLOSSARY.md, or recording or editing an ADR.
---

# Domain Modeling

Actively build and sharpen the project's domain model as you design. This is the *active* discipline: challenging terms, inventing edge-case scenarios, and writing the glossary and decisions down the moment they crystallise. (Merely *reading* `GLOSSARY.md` for vocabulary is not this skill: that's a one-line habit any skill can do. This skill is for when you're changing the model, not just consuming it.)

## File structure

First inspect repository guidance and existing terminology and decision records. Follow their locations, context boundaries, formats, and numbering; do not create a second glossary or ADR tree because it uses different names. The paths below are defaults when no convention exists, not required migrations.

Most repos have a single context:

```
/
├── GLOSSARY.md
├── docs/
│   └── adr/
│       ├── 0001-event-sourced-orders.md
│       └── 0002-postgres-for-write-model.md
└── src/
```

If a `GLOSSARY-MAP.md` exists at the root, the repo has multiple contexts. The map points to where each one lives:

```
/
├── GLOSSARY-MAP.md
├── docs/
│   └── adr/                          ← system-wide decisions
├── src/
│   ├── ordering/
│   │   ├── GLOSSARY.md
│   │   └── docs/adr/                 ← context-specific decisions
│   └── billing/
│       ├── GLOSSARY.md
│       └── docs/adr/
```

Create files lazily: only when there is a meaningful agreed term or decision to record. Use the existing location; otherwise a root `GLOSSARY.md` and `docs/adr/` are reasonable defaults. Do not create empty documents or reorganize existing records just to fit these examples.

## During the session

### Challenge against the glossary

When the user uses a term that materially conflicts with the existing glossary, surface the difference. "Your glossary defines 'cancellation' as X, but you seem to mean Y. Which is it?" Check whether context or an already accepted decision resolves it before asking again.

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. "You're saying 'account': do you mean the Customer or the User? Those are different things."

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios that probe edge cases and force the user to be precise about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it: "Your code cancels entire Orders, but you just said partial cancellation is possible. Which is right?"

### Record agreed terms inline

When a term is agreed and documentation edits are in scope, update the existing glossary as it is resolved. Follow its format; use [GLOSSARY-FORMAT.md](./GLOSSARY-FORMAT.md) as a default. Label unresolved suggestions as proposals in the current discussion or working artifact, rather than inserting them as accepted definitions. Never silently replace an accepted meaning: make the old/new distinction and affected context explicit, and apply only the agreed change. Preserve existing authorization; merely reading the glossary does not authorize unrelated edits.

`GLOSSARY.md` should be totally devoid of implementation details. Do not treat `GLOSSARY.md` as a spec, a scratch pad, or a repository for implementation decisions. It is a glossary and nothing else.

### Offer ADRs sparingly

Only offer to create an ADR when all three are true:

1. **Hard to reverse**: the cost of changing your mind later is meaningful
2. **Surprising without context**: a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off**: there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the ADR. Follow the repository's ADR format, using [ADR-FORMAT.md](./ADR-FORMAT.md) only as a default. Make proposed versus accepted status explicit; recording a proposal does not establish agreement. Preserve or supersede an existing accepted decision according to the repository convention rather than silently rewriting its history.
