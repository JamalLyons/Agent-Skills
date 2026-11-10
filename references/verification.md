# Verifying a sub-agent's step

Go through these after every step. Most bad commits come from trusting the agent's report instead of the diff.

## 1. Scope
- `git status --porcelain`: list every changed or new file. Is each one in the step's scope?
- Untracked junk: build output, `.DS_Store`, scratch scripts, logs, editor files. Remove them or ask the agent to.
- Unrelated churn: reformatted files, renamed symbols elsewhere, version bumps nobody asked for.

## 2. The diff itself (`git diff` and `git diff --stat`)
- **Stubs passed off as done:** `TODO`, `FIXME`, `unimplemented`, empty bodies, `return true; // for now`, hard-coded values standing in for real logic.
- **Tests weakened to make them pass:** deleted tests, loosened assertions, `skip` or `xfail`, catch-all exception swallowing, mocks that make a test meaningless.
- **Edge cases from the acceptance criteria:** is each one handled in the code *and* covered by a test?
- **Safety:** no secrets or tokens, no disabled safety checks, no `--no-verify`, nothing that bypasses security or permission prompts.
- **Consistency:** does it use the interfaces from earlier steps instead of re-implementing them? Does it match the naming, error-handling and file-layout conventions?

## 3. Run it yourself
- Run the step's targeted verification commands.
- Run the full build and test suite. Compare with the baseline taken during recon: a new failure belongs to this step; a pre-existing one doesn't.
- Run lint and format if the repo has them.
- For user-facing behaviour (a CLI, an endpoint), actually invoke it once when you can. A passing unit test isn't proof that the binary works.

## 4. Acceptance criteria
Tick off each criterion with evidence (a test name, a command's output, a line of code). Anything you can't tick off means rework.

## Verdict
- **Commit** if everything above is clean.
- **Rework** with specific notes (file:line, what's wrong, what's expected).
- **Fix it yourself** only if the fix is trivial (a few lines) and making it is clearer than explaining it.
