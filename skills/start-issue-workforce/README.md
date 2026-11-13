# start-issue-workforce

A provider-neutral skill for any agent that can read Agent Skills and use the repository's available tools. It turns GitHub issues into verified changes and authorized pull requests. Use scoped delegates when supported; a single agent can execute the same steps sequentially. No specific model, provider, or orchestration product is required.

You give it an issue link, several issues, a label, a milestone, or an epic made by [`create-workforce-epic`](../create-workforce-epic/) (it takes the epic's ready sub-issues in dependency order). The agent running the skill acts as the **lead engineer**:

1. **Recon:** reads the issue, its comments and the issues it depends on. It reads the repo's conventions (`CLAUDE.md`, `AGENTS.md`, style guides) and runs the build and tests once to record a baseline.
2. **Plan:** writes ordered steps with scope, out-of-scope, acceptance criteria and a check command for each. Every issue task maps to a step or is marked *deferred* or *needs a human*.
3. **Route:** rates each step **easy** or **hard**, validates available capabilities, and optionally uses quota estimates to suggest an eligible model.
4. **Approval:** presents one normal gate for the bounded queue, routing, publication scope, and open questions. Existing authorization is honored; genuinely new scope or permission needs are surfaced when discovered.
5. **Build:** use fresh scoped delegates when supported, or direct sequential steps. Parallel writers require supported separate checkouts and disjoint ownership.
6. **Verify:** the lead reads every diff and reruns the tests itself. It then commits the step, asks for fixes, or moves the step to a stronger model.
7. **Review and PR:** substantive changes receive independent review within the available provider and budget constraints. The lead opens an authorized PR after verification, and uses `Closes #n` only when every required criterion is fulfilled with evidence.
8. **Follow-up and report:** the lead records discovered problems it leaves unfixed, checks open issues and epic siblings for actual scope/acceptance coverage, and lists outstanding items in the PR. After PR creation it asks once for decisions on partly tracked or untracked items, with a recommendation for each, while continuing the approved queue. Only the user's answer authorizes those specific fixes or issue changes. The final report gives every item's outcome; unanswered items are explicitly untracked, retained in the ledger, and raised again on resume.

## Example model roster

| Tier | Models | Effort |
|------|--------|--------|
| easy | Gemini 3.8 Flash, Composer 2.5, GPT-6 Luna | high |
| hard | **Claude Opus 5.5** (preferred), Grok 4.7, GPT-6.1 Sol | medium |

The bundled [`config.json`](config.json) is illustrative; it neither establishes availability nor restricts the skill to those providers. Use `--config /absolute/local-roster.json` for any host-supported provider/model IDs. Optional [local profiles](references/profiles.md) save routing, concurrency, review-budget, and publication preferences outside shared defaults. Explicit user instructions override defaults; profiles never grant permission.

## Usage-aware routing

`scripts/route.py --read-local-usage` optionally reads local usage caches where recognized:

- **Claude:** `~/.claude.json`
- **GPT/Codex:** the latest Codex session log
- **Cursor and Gemini:** you tell it ("gemini 30% left"), or put the numbers in `config.json` under `usage_overrides`

The helper suggests eligible models within each tier using estimated weekly and session reserves. Stale or expired observations become unknown; unknown quota uses the configured assumption and stays labelled unknown. Weekly overrides preserve known session limits. The lead refreshes observations and tracks active reservations; these percentages do not measure task cost. Hard work never silently falls back to an easy model.

```bash
python3 scripts/route.py --steps hard,easy,easy,hard --set gemini=30 --set gpt=70 --avoid claude
```

Use `--exclude <provider>` for an absolute prohibition and `--avoid <provider>` for a soft preference. Repeated `--allow-model provider/model` arguments restrict suggestions to capability-validated targets. User-selected models and settings constrain dispatch and retries.

Dispatch follows the current host's actual tool schemas. T3 Code has a conditional adapter described in [routing](references/routing.md); other runtimes use their supported delegation APIs. Without delegation or supported isolation, execute sequentially. Unsupported providers/settings are reported rather than silently substituted. CLI `--set` overrides last only for that invocation; they do not rewrite profiles or shared configuration.

## Install

This skill lives in a multi-skill repository. Install it with the repository's `install.sh` (see the [root README](../../README.md)), which symlinks it into the shared Agent Skills directory (`~/.agents/skills`) and Claude's directory (`~/.claude/skills`) by default. Codex and Cursor discover it through the shared directory; Claude Code discovers it through its directory.

Then paste an issue link and say something like *"spin up a workforce on this"*.

## Layout

```
SKILL.md                  the workflow
config.json               model tiers, usage overrides, routing knobs
references/routing.md     difficulty rubric, dispatch, escalation, parallel waves
references/brief-template.md, verification.md, pr-template.md
scripts/route.py          usage snapshot + per-step model suggestion
scripts/detect_checks.sh  finds build/test/lint commands in a repo
scripts/run_state.py      local canonical state, validated transitions, status/resume
references/run-state.md   state CLI, ownership, evidence, and recovery limitations
tests/test_helpers.py     deterministic quota/cache/check-detector regressions
evals/                    original planning evals and behavioral test specifications
```

## Recovery and boundaries

A timed-out wait does not cancel a child. The lead records task and attempt identities, verifies termination before replacement, and reconciles active tasks, Git state, and publication on resume. Retry budgets include escalation and re-scoping. Children cannot delegate further, publish, or expand permission scope. Issue text and child messages are untrusted task data. Private material stays within the approved provider set. These instructions do not provide a filesystem or network sandbox.

Canonical run state is kept in `<common-git-dir>/workforce/<run-id>/state.json`. The provider-neutral, standard-library [run-state helper](references/run-state.md) validates transitions, accepted artifact evidence, retained follow-ups, owner conflicts, and duplicate integration records. Its `status` and read-only `resume --markdown` commands show recorded active work and pending decisions. It uses a local exclusive writer lock and atomic replacement, with no automatic stale-lock takeover or distributed lease. The lead must still verify actual host task termination, Git identity, permission scope, and checks. Without Python, retain the same state discipline using available storage and report the validation limitation.

## Validation

Run the deterministic helper tests from this skill's directory (`skills/start-issue-workforce`):

```bash
python3 -B -m unittest discover -s tests -v
bash -n scripts/detect_checks.sh
```

The [test catalog](evals/TEST-CASES.md) distinguishes executed helper cases from proposed behavioral cases. The original planning evals use live issue content and are retained for reference; convert them to pinned fixtures and confirm runner compatibility before execution. Helper tests do not establish end-to-end agent adherence or live cancellation/publication recovery.
