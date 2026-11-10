# Sub-agent brief template

Fill in every section. The sub-agent sees nothing but this text. It hasn't read the issue, the plan, the earlier steps or the repo docs. If something matters, put it in.

The brief may go to any model (Claude, GPT, Grok, Gemini, Composer), each running in its own harness with its own tools. So write it as plain engineering instructions: no Claude-specific tool names, no "use the Agent tool", and nothing that assumes it can see this conversation.

Keep it concrete: real paths, real function names, real commands. "Follow existing patterns" is useless. "Mirror how `src/actions/click.cpp` registers itself in `ActionRegistry`" is useful.

---

```markdown
You are implementing ONE step of a larger change in the repo at <absolute repo path>, on branch <branch>.
You are a scoped implementer: do this step well, do nothing else.

## Context
<2-4 sentences: what the overall issue is trying to achieve and where this step fits.
 e.g. "Issue #4 adds a CLI so bots can run without the editor. Step 1 (done) added
 BotRunner::runByName() in src/core/bot_runner.hpp. This step adds the CLI front-end on top.">

## Your task
<The step goal in 1-3 sentences.>

## Acceptance criteria
- <specific, checkable behaviour>
- <edge case + expected behaviour>
- <tests that must exist>

## Where to work
- Files you will likely create/modify: <paths>
- Existing code to read first: <paths + what to learn from each>
- Interfaces from earlier steps you must use (don't redefine): <signatures>

## Out of scope: do not touch
- <areas/files/features reserved for other steps>
- Don't reformat or refactor unrelated code, even if it's ugly.

## Repo conventions
<The rules that matter for this step, pulled from CLAUDE.md, STYLE.md etc.: naming, error
 handling, test framework, file layout, formatting tool. Quote briefly; don't paste whole docs.>

## Verify before you finish
Run these and make them pass:
    <build command>
    <test command (targeted, then full)>
    <lint/format command>
If something fails for a reason outside your step (a pre-existing failure), say so; don't "fix" it by
changing unrelated code or weakening tests.

## Rules
- Do NOT commit, push, switch branches, or rewrite git history. Leave changes in the working tree.
  (Parallel wave in its own worktree only: instead say "Commit your finished work to the current worktree branch with one commit; do NOT push, open PRs, or touch other branches.")
- Don't delete or weaken existing tests to make things pass.
- No placeholder/stub implementations presented as done. If you can't finish something, say exactly what's missing.
- If the brief is wrong (an interface doesn't exist, the approach can't work), stop and report instead of improvising a large redesign.

## Report back (keep it short)
1. What you changed (file → one line each)
2. Verification commands you ran and their results (pass/fail, counts)
3. Anything incomplete, assumed, or that the lead should double-check
```

---

## Rework message template (sent with SendMessage to the same agent)

```markdown
Review of your step. Please fix:
1. <file:line or symbol>: <what's wrong> → <what it should do>
2. ...
Keep everything else as is. Re-run <commands> and report the results.
```

Be specific. "Tests are weak" sends the agent guessing. "`parse_vars_test` doesn't cover a repeated `--var` with the same key; the expected behaviour is that the last one wins" gets fixed in one round.
