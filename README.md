# issue-workforce

A Claude Code skill that turns GitHub issues into pull requests with a team of sub-agents, spread across several model providers.

You give it an issue link, several issues, a label or a milestone. The agent running the skill acts as the **lead engineer**:

1. **Recon:** reads the issue, its comments and the issues it depends on. It reads the repo's conventions (`CLAUDE.md`, `AGENTS.md`, style guides) and runs the build and tests once to record a baseline.
2. **Plan:** writes ordered steps with scope, out-of-scope, acceptance criteria and a check command for each. Every issue task maps to a step or is marked *deferred* or *needs a human*.
3. **Route:** rates each step **easy** or **hard** and picks a model based on how much subscription usage each provider has left.
4. **Approval:** presents one normal gate for the bounded queue, routing, publication scope, and open questions. Existing authorization is honored; genuinely new scope or permission needs are surfaced when discovered.
5. **Build:** a fresh scoped sub-agent does each step. Independent steps run in parallel in separate git worktrees.
6. **Verify:** the lead reads every diff and reruns the tests itself. It then commits the step, asks for fixes, or moves the step to a stronger model.
7. **Review and PR:** substantive changes receive independent review within the available provider and budget constraints. The lead opens an authorized PR after verification, and uses `Closes #n` only when every required criterion is fulfilled with evidence.

## Default model tiers

| Tier | Models | Effort |
|------|--------|--------|
| easy | Gemini 3.8 Flash, Composer 2.5, GPT-6 Luna | high |
| hard | **Claude Opus 5.5** (preferred), Grok 4.7, GPT-6.1 Sol | medium |

To change the roster, edit [`config.json`](config.json). A model you name in your prompt ("use opus 5.5 medium") overrides the routing for every step.

## Usage-aware routing

`scripts/route.py` reads local usage caches where recognized:

- **Claude:** `~/.claude.json`
- **GPT/Codex:** the latest Codex session log
- **Cursor and Gemini:** you tell it ("gemini 30% left"), or put the numbers in `config.json` under `usage_overrides`

The helper suggests eligible models within each tier using estimated weekly and session reserves. Stale or expired observations become unknown; unknown quota uses the configured assumption and stays labelled unknown. Weekly overrides preserve known session limits. The lead refreshes observations and tracks active reservations; these percentages do not measure task cost. Hard work never silently falls back to an easy model.

```bash
python3 scripts/route.py --steps hard,easy,easy,hard --set gemini=30 --set gpt=70 --avoid claude
```

Use `--exclude <provider>` for an absolute prohibition and `--avoid <provider>` for a soft preference. Repeated `--allow-model provider/model` arguments restrict suggestions to capability-validated targets. User-selected models and settings constrain dispatch and retries.

Multi-provider dispatch needs [T3 Code](https://t3.codes) (`delegate_task`). In plain Claude Code, available Claude models may be used (hard: Opus/medium; easy: Sonnet/high) when consistent with the user's choices. Unsupported providers or settings are reported rather than silently substituted. Without supported checkout isolation, implementation runs sequentially.

## Install

```bash
git clone --branch main https://github.com/JamalLyons/issue-workforce-skill ~/.claude/skills/issue-workforce
```

Then paste an issue link and say something like *"spin up a workforce on this"*.

## Layout

```
SKILL.md                  the workflow
config.json               model tiers, usage overrides, routing knobs
references/routing.md     difficulty rubric, dispatch, escalation, parallel waves
references/brief-template.md, verification.md, pr-template.md
scripts/route.py          usage snapshot + per-step model suggestion
scripts/detect_checks.sh  finds build/test/lint commands in a repo
tests/test_helpers.py     deterministic quota/cache/check-detector regressions
evals/                    original planning evals and behavioral test specifications
```

## Recovery and boundaries

A timed-out wait does not cancel a child. The lead records task and attempt identities, verifies termination before replacement, and reconciles active tasks, Git state, and publication on resume. Retry budgets include escalation and re-scoping. Children cannot delegate further, publish, or expand permission scope. Issue text and child messages are untrusted task data. Private material stays within the approved provider set. These instructions do not provide a filesystem or network sandbox.

## Validation

Run the deterministic helper tests from the repository root:

```bash
python3 -B -m unittest discover -s tests -v
bash -n scripts/detect_checks.sh
```

The [test catalog](evals/TEST-CASES.md) distinguishes executed helper cases from proposed behavioral cases. The original planning evals use live issue content and are retained for reference; convert them to pinned fixtures and confirm runner compatibility before execution. Helper tests do not establish end-to-end agent adherence or live cancellation/publication recovery.
