# issue-workforce

A Claude Code skill that turns GitHub issues into pull requests with a team of sub-agents, spread across several model providers.

You give it an issue link, several issues, a label or a milestone. The agent running the skill acts as the **lead engineer**:

1. **Recon:** reads the issue, its comments and the issues it depends on. It reads the repo's conventions (`CLAUDE.md`, `AGENTS.md`, style guides) and runs the build and tests once to record a baseline.
2. **Plan:** writes ordered steps with scope, out-of-scope, acceptance criteria and a check command for each. Every issue task maps to a step or is marked *deferred* or *needs a human*.
3. **Route:** rates each step **easy** or **hard** and picks a model based on how much subscription usage each provider has left.
4. **Approval:** stops once to show you the plan, the routing and any open questions. After that it runs on its own.
5. **Build:** a fresh scoped sub-agent does each step. Independent steps run in parallel in separate git worktrees.
6. **Verify:** the lead reads every diff and reruns the tests itself. It then commits the step, asks for fixes, or moves the step to a stronger model.
7. **Review and PR:** two reviewers on different providers check the whole branch, then the lead opens a PR. It says `Closes #n` only when every task is done.

## Default model tiers

| Tier | Models | Effort |
|------|--------|--------|
| easy | Gemini 3.8 Flash, Composer 2.5, GPT-6 Luna | high |
| hard | **Claude Opus 5.5** (preferred), Grok 4.7, GPT-6.1 Sol | medium |

To change the roster, edit [`config.json`](config.json). A model you name in your prompt ("use opus 5.5 medium") overrides the routing for every step.

## Usage-aware routing

`scripts/route.py` reads live usage where it's available locally:

- **Claude:** `~/.claude.json`
- **GPT/Codex:** the latest Codex session log
- **Cursor and Gemini:** you tell it ("gemini 30% left"), or put the numbers in `config.json` under `usage_overrides`

Each step goes to the provider with the most headroom in its tier, so the work spreads out. The lead re-runs the script before every step, so routing follows your usage as it changes.

```bash
python3 scripts/route.py --steps hard,easy,easy,hard --set gemini=30 --set gpt=70 --avoid claude
```

Multi-provider dispatch needs [T3 Code](https://t3.codes) (`delegate_task`). In plain Claude Code, the skill falls back to Claude models only: hard steps go to Opus at medium, easy steps to Sonnet at high.

## Install

```bash
git clone https://github.com/JamalLyons/issue-workforce-skill ~/.claude/skills/issue-workforce
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
evals/                    test cases (run with `claude plugin eval .`)
```
