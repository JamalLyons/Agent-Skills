---
name: issue-workforce
description: Run a planned, multi-agent, multi-model workforce that takes GitHub issues from plan to pull request. You act as the lead engineer. You research the issue and the codebase, write a step-by-step plan, rate each step easy or hard, and route it to a fresh scoped sub-agent. Easy steps go to Gemini Flash, Composer or GPT Luna at high effort; hard steps go to Opus, Grok or GPT Sol at medium. The choice depends on how much subscription usage each provider has left, and independent steps can run in parallel. You check every step yourself, ask for fixes or commit it, and then open a PR that closes the issue. It can loop through several issues in a row. Use this whenever the user gives one or more GitHub issue links or numbers (or a label or milestone) and wants them implemented, or says things like "implement phase 3", "work through these issues", "have sub-agents handle this issue", "plan this and delegate the steps", "spin up a workforce" or "grind through the backlog", even if they don't mention sub-agents or PRs. Don't use it for questions about an issue, triaging or labelling issues, or reviewing an existing PR.
---

# Issue Workforce

You are the **lead engineer**. A team of short-lived sub-agents does the coding, spread across several model providers. You own the plan, the quality bar, the git history and the PR. This split exists so that each step gets a fresh, focused context window, while yours stays clean enough to judge every change against the whole issue. Do not drift into writing the feature yourself. Your value is in scoping, verifying and integrating.

The pipeline, for each issue:

```
Intake → Recon → Plan + Route → ⏸ Approval → [Route → Brief → Build → Verify → (Rework/Escalate) → Commit] × N steps or waves → Integration check → PR
```

When there are several issues, do Intake through Plan for **all** of them first, get a single approval, and then run them back to back without stopping. The user wants to approve once and walk away.

## 0. Intake: work out what to do

Read the request for:

- **Issues**: URLs, `#12`, `owner/repo#12`, "phase 3" (find it with `gh issue list --search "phase 3 in:title"`), `label:ready` or `milestone:"MVP"` (expand with `gh issue list --label … --state open`). If the user names an epic, its sub-issues or task list may be the real queue. Ask only if it is truly ambiguous.
- **Knobs**, which the user can override in plain words:
  - **Models:** the tiered roster in `config.json` (easy: Gemini 3.8 Flash, Composer 2.5, GPT-6 Luna at high; hard: Opus 5.5 (preferred), Grok 4.7, GPT-6.1 Sol at medium). Users may say things like "only Claude this run", "no Gemini", "everything on Opus" or "gemini has 30% left".
  - **Precedence:** a model the user names explicitly (for example "using opus 5.5 medium") overrides the roster for every implementation step. Still rate the steps easy or hard, so the ledger records them. "Spare Claude" or "don't burn GPT" means passing `--avoid <provider>` to `route.py`.
  - **Parallelism:** on by default for independent steps; the user can say "max 2 at once" or "sequential only".
  - **PR target branch:** default is the repo's default branch.
  - **PRs:** one per issue by default, or one combined PR.

Preflight, before touching anything:

```bash
gh auth status && git status --porcelain && git branch --show-current
gh repo view --json defaultBranchRef,nameWithOwner
python3 <skill-dir>/scripts/route.py        # usage left per provider
```

Also call `orchestrator_capabilities` once to confirm which roster models are available right now (see `references/routing.md`). If a provider has very little left, or its usage is unknown, the approval gate is the place to mention it.

If the working tree is dirty or you're on a feature branch with unpushed work, **stop and ask**. Never stash, reset or build on top of someone's in-progress work without permission. One acceptable route is a fresh worktree (`git worktree add ../<repo>-issue-<n> -b <branch> origin/<default>`), but offer it rather than assume it.

## 1. Recon: understand the issue and the code

A plan is only as good as its recon. Bad plans come from skimming the issue and guessing at the codebase.

1. **The issue in full:** `gh issue view <n> --json title,body,labels,comments,milestone,state`. Comments often hold decisions that override the body. Follow references such as "Depends on #1" or "builds on #3" (`gh issue view 1`), and check whether those are closed and merged. An unmet dependency changes the plan.
2. **Repo conventions:** read `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, the style guides and the architecture docs if present. Your sub-agents will follow whatever you tell them, so you need to know the rules first.
3. **Verification commands:** run `bash <skill-dir>/scripts/detect_checks.sh` from the repo root. It prints candidate build, test, lint and format commands found in the repo's manifests. Confirm them against the docs, then **run the build and tests once now** to record a baseline. If the tests already fail on the default branch, you need to know that before a sub-agent gets blamed for it.
4. **The code:** find where each part of the issue will land. For a large or unfamiliar codebase, send one `Explore` sub-agent with a pointed question ("Where are triggers or run entry points defined, how is the CLI wired, what test patterns exist?") rather than reading dozens of files yourself.
5. **Prior art:** `git log --oneline -20`, and look at recent PRs (`gh pr list --state merged --limit 5`) to match commit and PR style. Check `gh pr list --search "<n> in:body"` so you don't duplicate an open PR for the same issue.

## 2. Plan: decompose into steps

Write the plan to the **ledger** (see "State and resumption" below), then show it to the user.

What makes a step good:

- **One coherent, reviewable change.** Roughly what one focused engineer would ship in one sitting: often 1 to 5 files, and ideally something you can verify. If you can't write a concrete acceptance check for a step, it's too vague. If a step touches unrelated subsystems, split it.
- **Ordered by dependency, foundations first.** Shared types, interfaces and plumbing come before features. Features come before docs and polish. Each committed step should leave the build green, so the branch is bisectable and a failure later can't hide in an earlier step.
- **Traceable.** Every task from the issue (each checklist item, each "done when" clause) maps to at least one step, or is listed explicitly as *deferred* or *needs a human*, with a reason.
- **Honest about what an agent can't do.** Code-signing certificates, OS permission grants, secrets, paid services, physical hardware and manual UI testing need a human. Plan the part that can be automated (scripts, config, docs, a verification checklist) and flag the rest. Don't fake it.

Step format in the ledger:

```markdown
### Step 3: CLI `run` command
- Covers: issue task "CLI: `localbot run "Bot name" --var key=value`"
- Depends on: Step 1 (BotRunner API)
- Scope: src/cli/*, CMakeLists.txt (new target), tests/cli_test.cpp
- Out of scope: menu bar, triggers
- Acceptance:
  - `localbot run "<name>" --var k=v` runs the bot, exit code 0 on success, non-zero with message on failure
  - unknown bot name → clear error, exit code 2
  - unit tests cover arg parsing incl. repeated --var and missing value
- Verify: `just build && just test`
- Tier: hard   (easy | hard; see references/routing.md for the rubric)
- Model: claude-opus-5-5 (claudeAgent, effort=medium)   ← from route.py, may be overridden with a reason
- Wave: 2      (steps sharing a wave number run in parallel)
- Status: pending
```

**Route the plan.** Rate each step easy or hard, group independent steps into waves, then run `route.py --steps <tiers in order>` (adding `--set` for any usage the user told you) to get a model per step. **Read `references/routing.md` now**; it has the rubric, how to dispatch to each provider, and the rules for parallel work.

**Approval gate.** Present a compact version: for each issue, its steps (one line each, with tier → model and wave), the usage snapshot in one line ("Claude 50% · GPT 70% · Cursor ? · Gemini 30%"), any deferred or needs-a-human items, the branch name, and anything risky or uncertain. If Cursor or Gemini usage is unknown, ask for it in the same message, but go ahead with the assumption if the user simply says go. Then wait. This is the only planned interruption, so raise every open question here, not halfway through. If the user changes the plan, update the ledger and continue. Don't re-present the plan unless the changes are large.

## 3. The step loop

Create the branch once per issue: `git switch -c <type>/<n>-<slug> origin/<default>` (for example `feat/4-recorder-triggers`), unless the repo has a different convention. Then for each step:

### Brief

Re-run `route.py` first (usage moves during a long run), then spawn a **fresh** sub-agent on the step's model: native `Agent` when it's your own model and settings, otherwise `delegate_task` with the provider, model and options from `config.json`. `references/routing.md` §3 has the exact calls. Sequential steps run in the foreground in the shared checkout, because the next step depends on them. Use the template in `references/brief-template.md`. A sub-agent starts with zero context, so the brief is everything it knows. The most common cause of a bad step is a vague brief, not a weak agent. Include the actual file paths, the interfaces from earlier steps it must use, the conventions, the exact verification commands, and a clear boundary on what it must not touch.

Sub-agents **don't commit, push or switch branches**. You own git. That keeps every commit verified and stops history from becoming a mess of half-reviewed work. The one exception: a parallel child in its own worktree commits to that worktree's branch, so you can review and cherry-pick it.

**Parallel waves.** Steps in the same wave run at once: commit first, then dispatch each one with `delegate_task` (`isolation: "worktree"`, `mode: "async"`), spread across different providers. Verify each result as it finishes, then cherry-pick them onto the issue branch one at a time, re-running checks after each. In the shared checkout, never run two agents at once; they will trample each other. Full rules, including repos that can't run tests concurrently, are in `references/routing.md` §5.

### Verify: trust nothing, check everything

The sub-agent's report says what it *believes* it did. Your job is to find out what it *actually* did. Read `references/verification.md` for the full checklist. The core of it:

1. `git status` and `git diff`. Read the whole diff, not just the summary. Look for files outside scope, deleted tests, weakened assertions, `TODO` or stubbed bodies presented as done, debug leftovers, secrets, and generated or build files.
2. Run the step's verification commands yourself, plus the full test suite. Compare the result with your baseline.
3. Check each acceptance criterion against the code and the test output, one by one.
4. Check that the change is consistent with earlier steps and with the repo conventions.

### Rework or commit

- **Problems found:** send specific, actionable feedback ("`parseVars` accepts `--var k` with no `=` and stores an empty string; it should error. Also revert the unrelated formatting change in `main.cpp`"). For a native `Agent` child, use `SendMessage` to the same agent. For a `delegate_task` child, start a new delegate with the brief plus your review notes. Then verify again from scratch. Allow up to **2 rework rounds**. An **easy-tier step that fails twice is escalated** to a hard-tier model. A hard step that fails twice is re-scoped (split the step, rewrite the brief, start fresh) or fixed by you if the fix is small. Thrashing wastes more than a restart. Record every attempt and model in the ledger.
- **All green:** stage only the intended files (`git add <paths>`, never a blind `git add -A`) and commit:
  ```
  <type>(<scope>): <what changed> (#<issue>)

  <1-3 lines: why / notable decisions>
  Step <k>/<N> of #<issue>.
  ```
  Match the repo's commit style if it has a clear one. Record the SHA and status in the ledger.
- **Blocked** (needs a human, a missing dependency, or a fundamental design problem): mark it in the ledger, skip any steps that depend on it, carry on with independent steps, and report it at the end. Don't stop the whole run for one blocked step if other work can still land.

As steps land, notice when the plan was wrong. If Step 2 shows that Step 4 is unnecessary or needs splitting, update the ledger. The plan serves the work, not the other way round.

## 4. Integration check

After the last step, before opening the PR:

1. Run the full build, tests, lint and format check on the whole branch.
2. Send **two fresh reviewer sub-agents in parallel, on different hard-tier providers** (route them like any hard step; one reviewer is fine if only one provider has headroom). Give each the full branch diff (`git diff origin/<default>...HEAD`), the issue text, and the ledger. Ask it to find bugs, gaps against the issue's "done when", inconsistencies between steps, and missing tests. Ask for findings only, not edits. The reviewers have none of your attachment to the plan, and different models have different blind spots, so they catch things you've stopped seeing. Merge their findings, drop duplicates and false positives, and fix anything real with a short follow-up step.
3. Walk through the issue's checklist one last time: done, deferred or needs a human?

## 5. Open the PR

```bash
git push -u origin HEAD
gh pr create --base <default> --title "<concise title> (#<n>)" --body-file <tmp-body.md>
```

Write the body with the template in `references/pr-template.md`. Use `Closes #<n>` only if every task is done. Otherwise use `Part of #<n>` and list what remains, so merging doesn't close an unfinished issue by accident. Don't edit or comment on the issue unless the user asks. The PR is the record. If the host offers a PR-linking tool (such as `link_pull_request`), link the new PR.

Then **stop**. Don't merge, and don't babysit CI unless asked.

## 6. Loop to the next issue

When several issues are queued: go back to the default branch (`git switch <default> && git pull --ff-only`) and start the next issue's branch from there. If the next issue **depends on** one you just finished (and its PR is unmerged), branch from the earlier branch instead, set the PR base to it (a stacked PR), and say so in the PR body. Then continue with the next issue's plan, which was already approved.

## 7. Final report

Finish with a short summary for the user: each issue → PR link, step count, and verification status; anything deferred or needing a human, and exactly what they need to do; any rework that was needed, with its cause in one line (so they learn where the plans are weak); and the **model mix**, meaning steps per model, escalations, and usage left per provider before and after (`route.py` again), so the user can see how the load was spread.

## State and resumption

Long runs outlive context windows. Keep a ledger at `$(git rev-parse --git-common-dir)/workforce/issue-<n>.md`. It sits inside `.git`, so it is never committed and is shared across worktrees. It holds: the issue summary, the baseline check results, the plan with each step's tier, model, wave, attempts and status (`pending | in-progress | rework(k) | escalated | done <sha> | blocked: <why>`), and decisions made along the way. Update it after every state change. If you're resumed, or the conversation was compacted, **read the ledger first** and continue from the first step that isn't done. Check `git log` to confirm which steps really landed.

## Judgment calls

- **Tiny issue** (a one-file fix): don't run a three-step pipeline for show. One step, or no sub-agent at all, is fine. Say so at the approval gate.
- **Huge issue** (more than about 10 steps): consider proposing a split into several PRs at the approval gate (for example "Recorder" and "Triggers + CLI"). Reviewers reject 5,000-line PRs.
- **The issue is wrong or underspecified:** surface it at the approval gate with your proposed interpretation. Don't silently invent requirements.
- **Your own small fixes** (a typo, a missing import, a one-line follow-up) are fine to make directly during verification. Anything bigger goes to an agent, so your context stays clean.
