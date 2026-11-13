---
name: improve-codebase-architecture
license: MIT
description: Scan a codebase for deepening opportunities, present them as a visual HTML report, then grill through whichever one you pick.
---

# Improve Codebase Architecture

Surface architectural friction and propose **deepening opportunities**: refactors that turn shallow modules into deep ones. The aim is testability and AI-navigability.

This command is _informed_ by the project's domain model and built on a shared design vocabulary:

- When installed, read [codebase-design](../codebase-design/SKILL.md) for useful vocabulary and design heuristics. Preserve repository/domain terminology, API names, and code identifiers; a service or security boundary should keep that name. If the sibling skill is unavailable, assess caller complexity, change locality, testability, and useful isolation directly.
- Discover the repository's glossary and ADR conventions. They give names and context to existing contracts; do not re-litigate decisions without new evidence.

## Process

### 1. Explore

**Scope before you scan: YAGNI.** Deepening a module pays off by making future changes to it easier, so put extra weight on the parts of the codebase that have recently changed. Decide *where* to look before you look:

- If the user named a direction (a module, a subsystem, a pain point), take it, and skip the inference below.
- Otherwise, walk back a good stretch of the commit history (`git log --oneline`) to find the codebase's hot spots, the files and areas that keep coming up, and let those paths pull your attention first. If the changes are scattered with no clear hot spot, widen the net.

Read the project's domain glossary and relevant ADRs first, when present (`GLOSSARY.md` and `docs/adr/` are common defaults). Their absence does not block a review.

Walk the codebase directly, or use a fresh-context subagent when available and permitted by the host and user instructions. Don't follow rigid heuristics; explore organically and note where you experience friction:

- Where does understanding one concept require bouncing between many small modules?
- Where are modules **shallow**, with an interface nearly as complex as the implementation?
- Where have pure functions been extracted just for testability, but the real bugs hide in how they're called (no **locality**)?
- Where do tightly-coupled modules leak across their seams?
- Which parts of the codebase are untested, or hard to test through their current interface?

Apply the **deletion test** as a heuristic: where would complexity move if this layer disappeared, and what contract would be lost? A thin layer may protect authorization, compatibility, lifecycle, or independent ownership. Seek a concrete costly change, defect, or navigation problem before recommending consolidation; unchanged structure is the baseline alternative.

### 2. Present candidates as an HTML report

Use the host's supported artifact/render mechanism and its output requirements. Otherwise write a self-contained HTML file to the OS temp directory (`$TMPDIR`, else `/tmp`; `%TEMP%` on Windows), using a unique `architecture-review-<timestamp>.html` name. Return a file link if rendering is unavailable; if files cannot be created, give a concise text report with the same evidence and limitations. Do not invent tools or open a system browser unless requested. Save a durable summary in the repository's established location only when requested or already authorized.

Use inline CSS and SVG so the report works offline without external scripts. Choose graph, flow, sequence, or cross-section diagrams to fit each candidate. Each candidate gets a **before/after visualisation**.

For each candidate, render a card with:

- **Files**: which files/modules are involved
- **Problem**: why the current architecture is causing friction
- **Evidence and confidence**: a concrete costly change, defect, or code path, with source locations; separate observed friction from inferred benefits and unresolved questions
- **Solution**: plain English description of what would change
- **Benefits**: explained in terms of locality and leverage, and how tests would improve
- **Migration**: qualitative effort, compatibility/ownership risks, and the first independently verifiable step; name the behavior and regression coverage that must survive
- **Before / After diagram**: side-by-side, custom-drawn, illustrating the shallowness and the deepening
- **Recommendation strength**: one of `Strong`, `Worth exploring`, `Speculative`, rendered as a badge

End with the top recommendation and why its expected benefit justifies its effort and risk over leaving the structure alone. Reserve `Strong` for concrete supporting evidence and a credible migration path; explain what evidence would strengthen a speculative candidate.

Use established domain names and the repository's architectural terms. Connect those concepts to exact code identifiers so readers can locate the evidence; shared vocabulary should clarify the proposal rather than rename the system.

**ADR conflicts**: if a candidate contradicts an existing ADR, only surface it when the friction is real enough to warrant revisiting the ADR. Mark it clearly in the card (e.g. a warning callout: _"contradicts ADR-0007, but worth reopening because…"_). Don't list every theoretical refactor an ADR forbids.

See [HTML-REPORT.md](HTML-REPORT.md) for report structure, diagram patterns, and styling guidance.

Do not design detailed replacement interfaces or implement code during an audit alone. If no justified candidate exists, report that and stop without manufacturing a refactor. Otherwise ask which candidate to explore, unless the user already selected one or authorized the next step. An architecture recommendation does not by itself authorize implementation.

### 3. Grilling loop

Once the user picks a candidate, use [grill-me](../grill-me/SKILL.md) when available, or directly resolve consequential open decisions in bounded rounds: constraints, dependencies, the interface shape, and tests that must survive. Do not repeat settled questions or force an interview for an already specified implementation.

When terminology or decision recording is within the requested scope, use [domain-modeling](../domain-modeling/SKILL.md) when available and follow existing document conventions:

- **A new or sharpened domain term?** Record the accepted definition in the existing glossary when authorized; keep proposals visibly separate. Do not create or edit repository documents merely because an audit used a new phrase.
- **User rejects the candidate with a load-bearing reason?** Offer an ADR, framed as: _"Want me to record this as an ADR so future architecture reviews don't re-suggest it?"_ Only offer when the reason would actually be needed by a future explorer to avoid re-suggesting the same thing; skip ephemeral reasons ("not worth it right now") and self-evident ones.
- **Want to explore alternative interfaces for the deepened module?** Read [codebase-design](../codebase-design/SKILL.md) and use its design-it-twice comparison pattern, with permitted subagents or direct passes.
