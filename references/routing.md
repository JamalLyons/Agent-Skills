# Routing: picking a model for each step, and running steps in parallel

The roster and the defaults live in `config.json` at the skill root. The user edits that file to change models; this document explains how to use it.

| Tier | Models (provider) | Setting |
|------|-------------------|---------|
| **easy** | Gemini 3.8 Flash (`antigravity`), Composer 2.5 (`cursor`), GPT-6 Luna (`codex`) | high (Composer has no effort setting, so it runs on its defaults) |
| **hard** | **Claude Opus 5.5 (`claudeAgent`, preferred)**, Grok 4.7 (`cursor`), GPT-6.1 Sol (`codex`) | medium |

Fast models run at high effort; strong models run at medium. A strong model at medium is already enough for most hard steps, and a fast model at high effort gets more done reliably.

## 1. Rate each step easy or hard

Rate each step when you write the plan, and record it in the ledger (`- Tier: easy`).

**Easy**: well specified, follows an existing pattern, and stays local. A competent junior engineer could finish it from the brief alone.
- Docs, README and changelog updates; example files; config and build-file entries modelled on existing ones
- Tests for behaviour that already exists; fixtures; test data
- Boilerplate that mirrors an existing example ("add a `scroll` step like `src/steps/click.cpp`")
- Small UI wiring to an API that already exists; renames; mechanical migrations with a clear rule

**Hard**: needs judgment, or other steps depend on getting it right.
- A foundation step that defines interfaces or types later steps build on
- Cross-cutting refactors; concurrency and threading; native OS APIs; security, permissions or secrets
- Data or schema migrations; vague requirements; debugging a failure whose cause isn't known
- Anything where a subtle mistake would pass the tests but break later steps

**If unsure, rate it hard.** A failed easy step costs a rework round plus a re-dispatch, which is more than the saving.

## 2. Get the routing suggestion

```bash
python3 <skill-dir>/scripts/route.py --steps hard,easy,easy,hard,...   # one entry per step, in plan order
```

It prints a **snapshot of usage left** for each provider:
- **Claude:** from `~/.claude.json`, live.
- **Codex/GPT:** from the latest Codex session log, live as of the last Codex session.
- **Cursor and Antigravity/Gemini:** these keep no local limit data, so they show as *unknown* and are assumed to have 50% left.

Then it prints a **suggested model per step**. The suggestion is a greedy spread: each step goes to the tier model whose provider has the most headroom. Two bonuses apply: one for the preferred model, and a use-it-or-lose-it bonus when a provider's weekly limit resets within 24 hours. The provider's headroom is then reduced, so work spreads out across providers. Providers with less than 15% left this week, or less than 10% left in their 5-hour window, are skipped.

When the user tells you usage in plain words ("gemini's at 30% left", "lots of GPT left"), pass it through: `--set gemini=30 --set gpt=70`. The user's numbers beat a stale live reading. "Spare Claude" or "don't burn X" → `--avoid claude`, which makes that provider a last-resort fallback. The aliases gemini, gpt, claude, grok and composer map to providers. Grok and Composer both run on Cursor, so they share Cursor's quota.

Treat the output as a strong default, not an order. Override it when you have a reason, and say why in the ledger. For example:
- Keep the single most important foundation step on the preferred model unless Claude is nearly out.
- Keep a closely related pair of steps on one model so the style stays consistent.

Your own lead work (planning, verifying, reviewing) runs on Claude too. **If Claude's 5-hour window runs out, the whole run stops**, not just one step. On long runs, leave Claude headroom: if Claude's 5-hour window is below about 30%, route hard steps elsewhere or warn at the gate. If you are cut off anyway, the ledger lets the run resume after the reset. Keep the ledger current after every step for exactly this reason.

**Re-run `route.py` before each step or wave.** It's cheap, and usage changes during a long run: a provider resets, or one gets used up. Re-routing between steps is how the workforce reacts to usage in real time.

## 3. Dispatch

First call `orchestrator_capabilities` once per run to confirm which models are available right now. Drop any roster model that isn't listed and tell the user. Then for each step:

- **The step's model is your own model, and its options match yours** (for example, Opus at medium while you are Opus at medium): use the native `Agent` tool (`model: "opus"`, `effort: "medium"`).
- **Any other model:** use `delegate_task` with `target: {providerInstanceId: <provider>, model: <model>, options: <options from config>}`, `role: "implementation"`, and the brief as `task`.
  - A sequential step runs in the shared checkout: `isolation: "shared"`, `mode: "wait"` with a generous `timeoutMs` (for example 1800000). A timeout doesn't cancel the child.
  - The child sees nothing but `task`, so the brief has to stand on its own (it already should).
- Don't poll a running delegate. Follow the `next` hint the tool returns, and `task_cancel` any delegate you abandon.

**Not running inside T3?** Without `delegate_task`, only Claude models are available through `Agent`. Use **hard → `opus` at `medium`** and **easy → `sonnet` at `high`**.

**When a dispatch fails** (rate limit, model unavailable, or a provider error): mark that provider as used up for this run, send the step to the next candidate in its tier, and carry on. Don't stall the run on one provider.

## 4. Rework and escalation

- **Native `Agent` child:** send the review notes to the same agent with `SendMessage`.
- **`delegate_task` child:** start a **new** `delegate_task` with the original brief plus a "Review of the previous attempt" section. Its changes are still in the working tree. Each re-check is a fresh delegate, not a message into the old thread.
- **Easy step failed verification twice:** escalate it. Re-dispatch to the best hard-tier model with the brief plus everything learned. A weak model making the same mistake a third time wastes more than one strong run.
- **Hard step failed twice:** re-scope it (split it or rewrite the brief), or fix it yourself if the fix is small.
- Record every attempt in the ledger (`- Attempts: composer-2.5 ✗ (missed edge case), claude-opus-5-5 ✓`). The final report uses this to show which models struggled with what.

## 5. Parallel waves

Several sub-agents at once can save a lot of wall-clock time when the plan has independent steps. For example, once a foundation step lands, "CLI", "menu bar" and "docs" may each depend only on it. Group them into **waves**.

A step can join a wave only if:
- it doesn't depend on any other step in the same wave, **and**
- the waves' scopes don't overlap. Two steps that both edit `CMakeLists.txt` or the same registry file will conflict. Put them in different waves, or have one step own the shared file and give the other an explicit "don't touch X; the lead will add the entry".

How to run a wave:

1. **Commit everything first.** Worktree children start from the parent's last commit, and uncommitted edits are left out.
2. Spread the wave across providers. This is the whole point of having several: three steps on three providers finish faster and drain no single 5-hour window. Use 2 to 4 children per wave; more than that and verifying them becomes the bottleneck.
3. Dispatch each one with `delegate_task`, `isolation: "worktree"`, `mode: "async"`. In a worktree, the brief **may allow a commit** on the worktree's own branch, because that's how the work gets back to you. Pushing, PRs and touching other branches are still forbidden.
4. **Check shared resources.** Some repos can't run builds or tests concurrently: a shared database lock, fixed ports, a single build directory. If yours can't, tell the wave's children to build only and run targeted tests. You then run the full suite serially after merging.
5. As each child finishes, verify its worktree diff as usual (`references/verification.md`). Then cherry-pick it onto the issue branch, one at a time, re-running the build and tests after each one. If a cherry-pick conflicts, resolve it yourself if it's trivial; otherwise send that step back as a normal sequential rework.

Parallelism also helps outside implementation:
- **Recon:** fan out 2 or 3 read-only research agents on separate questions, cheapest tier.
- **Integration review:** use **two reviewers from different hard-tier providers** (for example Opus and Grok). Different models have different blind spots, and two reviews in parallel cost no extra wall-clock time. Merge their findings and drop duplicates.

Default to sequential when steps form a chain or touch the same files. Parallelism is an optimisation, not a goal.
