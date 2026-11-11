# create-workforce-epic

A Claude Code skill that turns a large GitHub issue into a queue of PR-sized sub-issues for [`start-issue-workforce`](../start-issue-workforce/).

You give it an epic. The agent acts as **tech lead**:

1. **Recon:** reads the epic, its comments, linked work, and the repository (conventions, CI, real test commands).
2. **Decompose:** writes a plan of tasks. Each task is one PR, with scope, owned paths, checkable acceptance criteria, verification commands, an easy/hard tier, and real blocked-by dependencies. Work only a person can do becomes a *human* task. Every epic criterion is covered by a task or explicitly deferred.
3. **Approval gate:** validates the plan, does a dry run against GitHub, and shows a table, dependency graph, coverage, and the exact writes. Nothing is created yet.
4. **Apply:** creates the task issues, links them as **native sub-issues** of the epic, and adds **native blocked-by** dependencies.
5. **Stop:** reports the ready set and suggests running `start-issue-workforce` on the epic. It does not launch it.

GitHub is the queue: progress shows on the epic, merging a task's PR (`Closes #n`) closes its sub-issue, and `epic_status.py` shows what is ready next.

## Scripts

```bash
# offline
python3 scripts/apply_plan.py validate plan.json
python3 scripts/apply_plan.py render plan.json --task T2

# reads GitHub, writes nothing
python3 scripts/apply_plan.py apply plan.json

# writes (after approval); safe to re-run
python3 scripts/apply_plan.py apply plan.json --execute

# queue view: table, --json, or --ready (issue numbers in dependency order)
python3 scripts/epic_status.py --repo owner/name --epic 42
```

`apply` is idempotent. Each created issue carries a hidden marker with the epic and task key, so a re-run after a failure or lost response reuses what exists instead of duplicating it. It never edits, closes, or re-parents existing issues. The plan format is in [references/plan-format.md](references/plan-format.md), with a complete [example](references/plan.example.json).

`epic_status.py` only treats a blocker as finished when a merged PR or a commit closed it (or it is a human task closed as completed). A closed issue with no merged work shows as `check`, not `ready`.

Both scripts use the GitHub CLI (`gh`), authenticated for the target repo, and the Python standard library only.

## Layout

```
SKILL.md                      the workflow
references/decomposition.md   sizing, slicing, dependencies, human tasks, tiers
references/plan-format.md     plan JSON fields and rendered issue body
references/plan.example.json  complete valid plan
references/github.md          endpoints, idempotency, status semantics, limits
scripts/epiclib.py            validation, rendering, markers, gh client
scripts/apply_plan.py         validate / render / apply
scripts/epic_status.py        queue status from GraphQL
tests/test_epic.py            offline tests with a simulated GitHub
evals/                        behavioural test specifications
```

## Validation

```bash
python3 -B -m unittest discover -s tests -v
```

The tests simulate GitHub, including lost responses, duplicate markers, issues under another parent, and a missing dependencies API. They do not prove the planning agent follows the prose; see [evals/TEST-CASES.md](evals/TEST-CASES.md).
