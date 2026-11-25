# State and recovery

Read when creating run state and before any resume or context-compaction recovery. The helper CLI is in [run-state](run-state.md).

## State

Resolve the common Git directory to an absolute path. Keep canonical `<common-git-dir>/workforce/<run-id>/state.json` with repository, approved queue, scope, constraints, and owner. Use the local [run-state helper](run-state.md) to validate transitions, persist atomically, and generate status/resume views when Python is available; otherwise retain the same facts and checks with available storage and disclose missing executable validation. Supporting issue/check artifacts may be linked from state, but do not maintain a second writable ledger. Only one lead writes state; children report to it. Reconcile existing ledgers before migrating. Detect another active owner before resuming, and use a different run ID for a separate run. Never store secrets/full logs there. The helper records observations; it cannot prove task termination, permission, Git ancestry, or test success.

Persist approval/scope, issue snapshot, base/head/branch/PR identities, baseline and acceptance evidence, step dependencies/ownership, all attempts/task IDs, budgets/deadlines, active or pending questions, integrated SHAs, reviewer findings/dispositions, publication state, and next safe action. Suggested states: pending, running, waiting, verifying, rework, accepted, integrated, blocked, cancelled. A child report is not acceptance evidence.

## Resume

On resume read canonical state and its referenced evidence first; reconcile actual Git state, active tasks, host continuation instructions, and remote publication before doing work. Do not blindly restart the first unfinished step. Confirm an old child is terminal/cancelled before assigning its files; ignore late results from superseded generations. If task state cannot be established, preserve the checkout and report the uncertainty rather than start another writer. User stop/cancel applies to active children too. Retain unanswered items and ask again on resume after rechecking tracker coverage; do not infer approval from an earlier unanswered question.
