---
name: docs-drift
description: >
  Sweep repository documentation against code, tests, workspace layout, CI,
  and issue/PR state, then update stale docs in place. Use when the user asks
  for a docs-drift sweep, notices documentation drift, or asks to refresh
  README, ROADMAP, CONTRIBUTING, AGENTS.md, API/module doc comments, CLI help,
  website claims, or issue references that no longer match the project.
---

# Docs drift

Refresh project documentation that has drifted from the code, tests, CI, or issue tracker. Edit documentation in place. Do not change runtime behavior, and do not mutate external issue/PR state unless the user explicitly asks.

Use the host's available tools to read files, run local read-only verification or evidence scripts, and edit docs. Tracker CLIs or integrations (such as `gh`) are optional; if unavailable or offline, report that limitation and do not guess issue or PR state.

## Evidence first

Gather observed facts from the repository before editing anything:

1. If the repository provides a docs-drift or doc-verification script or task-runner recipe (for example `just docs-drift`, `scripts/docs-drift.sh`, or a CI doc check), read it and run it first if it is read-only. Reason from that output and the files it names.
2. Otherwise, inspect the primary sources of truth directly:
   - Package/workspace manifests (`package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, etc.)
   - CI workflows (`.github/workflows/`, etc.) and task runners (`Makefile`, `justfile`, `Taskfile`)
   - CLI entrypoints and `--help` definitions
   - Test directories and unit/integration test files
   - Issue/PR state via available tracker tools for any issue or PR numbers cited in docs
3. Do not correct a status, command, path, or issue state from memory.
4. Treat any automated pattern hit as a lead, not proof. Re-read the surrounding sentence against the evidence before changing it so you do not revert a true statement.

## Scope

Check these surfaces when present, and fix the ones that are wrong:

- Root docs: `README.md`, `ROADMAP.md`, `CONTRIBUTING.md`, and current guides
- Agent instruction files: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.cursor/rules/`, or per-package equivalents
- `docs/`, except the historical exclusions below
- Package or crate `README.md` files
- Module and public API doc comments (for example rustdoc `//!` / `///`, JSDoc, Python docstrings)
- CLI help text (flag/subcommand descriptions and `about` strings)
- Website or landing-page claims (for example `website/` or `docs/` marketing pages)
- Doc references to issues, pull requests, epics, and milestones

Compare them against:

- **Code and config**: Does the API, command, flag, path, environment variable, or task-runner recipe still exist? Does contributor advice still match what the code, CI, and `AGENTS.md` enforce?
- **Issue and PR state**: Are closed items described as open, or do phase/epic/roadmap statuses disagree with the tracker or the roadmap's own sequencing notes?
- **Workspace layout**: Do listed packages, crates, modules, and excluded/parked directories match the root manifest?
- **Test layout**: Do documented test paths and commands match where tests actually live?

## What not to rewrite

- **Historical snapshots**: Dated reviews, audit reports, eval baselines, and one-off validation logs (for example `docs/reviews/`, `docs/audits/`, `*-validation.md`) are records of a past point in time. Do not modernize them. If a current doc cites a snapshot as if it described today's tree, fix the citation in the current doc.
- **Accepted ADRs**: An accepted ADR's Context section describes the codebase when the decision was made; do not modernize it. Its Decision section is the owner decision. Change a status line only when it makes a present-tense claim that code or tracker state proves false.
- **Vendored or submodule code**: Do not edit `vendor/`, third-party bundles, or git submodules as part of a docs-drift sweep.

## Categories

Label every finding with one of these:

| Category | Meaning |
|---|---|
| `stale fact` | A concrete claim (command, path, package/crate, test, flag, behavior) that is no longer true |
| `dead reference` | A link, issue, PR, or file path that does not resolve |
| `wrong status` | Open/closed, phase, or epic progress that disagrees with the tracker or the roadmap's own sequencing |
| `outdated advice` | Instructions a contributor or agent would follow that contradict `AGENTS.md`, CI, or the code |
| `missing doc` | A current fact a reader of that page needs and that page does not mention |

## Fix

1. **Categorize from evidence.** If the evidence does not prove a claim is wrong, leave the text unchanged and record it as unresolved.
2. **Edit in place.** Make the smallest change that makes the sentence true. Match the surrounding voice and heading style. Do not create a new summary document in the repo for the sweep.
3. **Do not describe goals as shipped.** Planned capabilities, reserved/empty packages, and unsupported platforms remain goals until tests or public commands exercise them.
4. **Follow current sequencing.** When a planning issue or roadmap sequencing note supersedes older epic text, follow the current sequencing and remove stale "gated on" language that no longer applies.
5. **Preserve behavior.** User-facing error strings, CLI exit codes, and runtime logic are behavior, not documentation. Do not change them in a docs-drift pass; list them under Recommendations unless the user explicitly asks for a behavior change.
6. **Defer owner decisions and tracker writes.** Anything requiring an owner decision, or mutating external tracker state (closing an issue, editing an issue body, ticking an acceptance box), goes under Recommendations unless the user explicitly asks.
7. **Respect deferred website/doc work.** If an open issue or repo note explicitly defers a website or doc redesign, do not redesign it; record the stale sentences and the blocking issue under Recommendations.

## Guardrails

- **Doc-only.** Make no engine, library, CLI logic, or test-behavior changes.
- **Respect architecture boundaries.** Follow the repo's module/platform boundaries (for example, keep platform-specific details out of portable core doc comments; point at the platform module instead). Any code violation noticed while reading goes under Recommendations, not as a drive-by code fix.

## Report

Summarize the sweep concisely (and include this format in a PR body when opening a PR):

```markdown
## Drift report

Evidence: `<command or sources checked>` at `<rev>` on `<date>`.

### Fixed
- **<category>** — `<path>` — what changed, why, and the evidence (file, test, CI, or issue state).

### Recommendations
- What was left undone, why it was not an in-repo doc edit, and what the owner would do.

### Checked, no change
- Areas that were read and still matched the code, CI, or tracker.
```
