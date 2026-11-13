---
name: bug-investigation
description: Diagnose an existing failure through reproduction, competing hypotheses, and discriminating evidence; make a bounded fix and regression check when requested. Use for debugging symptoms, intermittent failures, or regressions. A diagnosis-only request does not authorize edits or publication.
---

# Bug investigation

Turn a symptom into an evidenced explanation before changing behavior. Use the host's actual tools and repository conventions; no particular agent, model, tracker, or delegation API is required. Work directly unless scoped assistance is available and permitted.

## Establish the failure

- Separate the reported symptom, expected contract, and observations already verified. Read relevant code, tests, recent changes, and environment details before asking for facts you can obtain yourself.
- Resolve the requested scope: diagnose, reproduce, or fix. Preserve dirty/index/untracked work and record the revision or artifact under investigation. Use an isolated fixture when reproducing would conflict with user work.
- Inspect commands and scripts before running them. Prefer a local, minimal reproduction using synthetic inputs; a debugging request does not authorize production writes, credential changes, deployment, or publishing.
- Record the exact trigger, expected and observed outcomes, command/steps, environment, and frequency when relevant. Check whether the failure exists at the proposed baseline under equivalent conditions. A missing tool, service, or platform is an unavailable check, not reproduction or evidence of a code regression.

## Find a discriminating explanation

Trace the failing path and keep a short set of plausible hypotheses. For each, identify an observation that would distinguish it from the alternatives. Select the smallest useful experiment—an edge input, boundary observation, focused test, or temporary instrumentation—rather than changing several variables together.

Update hypotheses after each result. Keep observed facts separate from inference; a passing unrelated test or disappearance after a broad rewrite does not establish root cause. For intermittent failures, capture ordering/timing and resource state where possible; do not turn a finite successful run into a claim that a race is gone.

An explanation is strong enough to act on when it accounts for the trigger and consequence, fits the existing contract, and has evidence that rules out material alternatives. If evidence remains incomplete, report the leading hypothesis with its uncertainty instead of naming a proven cause.

## Fix within scope

For diagnosis-only work, stop after the explanation and proposed remedy; do not edit the project. When a fix is authorized:

1. Preserve or add a focused regression check at the seam that observes the failure. Confirm the check fails for the reported behavior before the fix when execution is available. Use a representative manual check when that better fits the failure; do not add irrelevant tests merely to satisfy a ritual.
2. Make the smallest coherent correction to the evidenced cause. Avoid unrelated refactoring, suppressed errors, weakened tests, or accepting a changed contract just to make the symptom disappear.
3. Repeat the reproduction and meaningful neighboring regressions on the changed artifact. Exercise the representative user path when available. State what unit tests, inspection, or a different platform cannot establish.
4. Remove only investigation-owned instrumentation or temporary artifacts. Preserve useful bounded evidence without credentials, full private logs, or unrelated user data.

## Stop and report

Keep experiments bounded to the uncertainty and risk. Honor the user's limits; when the next step requires unavailable access, a product decision, or a broader change, give the specific blocker and highest-value next observation. Do not repeat an unchanged failed approach indefinitely or expand scope to manufacture progress.

Finish with the symptom and reproduction status, evidenced cause or ranked hypotheses, changed behavior if any, actual checks/results tied to the artifact, remaining limitations, and the exact next action if blocked. Distinguish “fixed in this environment” from broader claims. Post tracker updates, push, or open a PR only when those actions are authorized.
