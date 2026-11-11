# Decomposition rubric

Two layers split the work. This skill turns an **epic into tasks**: each task is one GitHub sub-issue and one pull request. `start-issue-workforce` later turns each **task into steps** for sub-agents. Size tasks for the first layer only; do not pre-plan agent steps here.

## Task size

- **One task, one PR.** A reviewer can read it in one sitting, typically a few hundred changed lines. If a task needs two PRs, split it. If it would be a single trivial edit, merge it into a neighbour that touches the same area.
- **Leaves the default branch healthy.** After the PR merges, the build and existing tests pass. Feature flags, unused new modules, or additive APIs are fine ways to land partial capability.
- **Self-contained brief.** Someone who has not read the epic can do it from the issue body plus the repository.

## Slicing

1. **Foundation first.** Shared types, schemas, interfaces, migrations, or config that several tasks need become early tasks. Others are blocked by them.
2. **Vertical over horizontal.** Prefer "add export for one format end to end" over "all models", then "all controllers", then "all views". Vertical slices are independently reviewable and testable.
3. **Separate risky from routine.** Isolate security, concurrency, data migration, native APIs, and uncertain debugging into their own tasks so they get the hard tier and focused review.
4. **Tests ride with code.** Each task includes the tests for its behaviour. A standalone "write tests" task is only for a genuinely separate harness or fixture effort.
5. **Docs with the change** unless the epic asks for a distinct documentation deliverable.

## Ownership and parallelism

- `owned_paths` lists the files or directories a task is expected to change (globs allowed). It is a scheduling hint for the implementer and for `start-issue-workforce` waves, not a lock.
- Tasks that are not ordered by dependencies should own disjoint paths so they can run in parallel. `validate` warns when unordered tasks overlap: either order them with `blocked_by`, or move the shared change into a foundation task.
- Shared registries (route tables, dependency manifests, lockfiles, generated code) cause most conflicts. Give them to one task or a foundation task.

## Dependencies

- Add `blocked_by` only for a real need: the task uses code, an interface, data, or a decision produced by the blocker. Preferred order is not a dependency.
- Keep the graph shallow and wide. Long chains serialize the whole epic.
- External prerequisites that already exist as issues are `"#n"` blockers. A prerequisite with no issue becomes a task (when it is in scope) or an open question at the gate (when it is not).
- `start-issue-workforce` treats a blocker as satisfied only when it is closed **and** a merged PR or commit closed it, or it is a human task closed as completed.

## Human tasks

Use `kind: "human"` for work an agent cannot or should not do: product or design decisions, credentials and secrets, code signing and notarization, app store or vendor accounts, purchases, production deploys, legal or security sign-off, and manual verification on real hardware. Give each a concrete acceptance criterion that says what "done" means, so agent tasks blocked by it know when to start. Human tasks have no tier.

## Tiers

Use the `start-issue-workforce` rubric. **Easy:** well-specified, local, pattern-following work: docs, fixtures, mechanical migrations, small UI following an existing pattern. **Hard:** foundation interfaces, security, concurrency, native or platform APIs, data migrations, performance, uncertain debugging, or anything many other tasks depend on. If unsure, choose hard.

## Acceptance and verification

- Acceptance criteria are observable and checkable ("`GET /exports/:id` returns 404 for another user's export", not "export works well").
- Verification lists exact commands that exist in this repo (from manifests, CI, or docs), scoped where the tooling allows. If behaviour can only be checked manually, say how in acceptance and note it.

## Coverage

List every epic criterion in `criteria`. Each is `covered_by` one or more task keys or `deferred` with a reason (out of scope, separate epic, needs a decision). Every task should cover at least one criterion. A task that covers none is either missing a criterion or is scope creep.

## Size of the epic

Up to about 15 tasks is a workable epic. Beyond that, propose phases: one epic per phase, each delivering something usable, with later phases blocked by earlier ones. The script refuses more than 50 tasks in one plan.

## Examples

Good: *"Add `ExportJob` model and migration"* (hard, foundation, owns `src/models/export*`, `migrations/`), followed by parallel *"CSV export endpoint"* and *"Export button in report view"* (both blocked by the model, disjoint paths).

Too big: *"Build the export feature"*. Too small: *"Add `format` column"* on its own when the model task already touches that table. Horizontal: *"Write all export tests"* after the code tasks.
