# Validated run state

Use `scripts/run_state.py` when Python 3.10+ is available. It is a local, standard-library ledger helper, independent of agent provider and delegation API. It records lead observations; it does not dispatch, cancel, query Git, prove tests passed, or grant authorization.

## Canonical state and ownership

Resolve the repository's common Git directory, then keep one canonical `<common-git-dir>/workforce/<run-id>/state.json`. The run ID, repository, frozen issue references, scope/approval context, steps, artifact identities, and follow-ups live there. Store bounded evidence or links, not credentials or full logs. Use a different run ID for an independent run.

Every mutation uses an exclusive local `.lock` file plus atomic replacement of the JSON file. A persistent owner ID prevents accidental use by a different lead; it is not a credential or security boundary. The lock has no automatic expiry, lease, distributed-filesystem guarantee, or stale-process detection. If a lock survives a crash, inspect its recorded PID and the actual machine/task state before removing only that lock. Never infer that a writer or child is dead because time elapsed. On uncertain ownership, preserve the state and stop conflicting work.

Use a unique lead-session owner ID. Claim an unowned run before edits. For transfer, reconcile the old lead and all tasks, then have the recorded owner release the run before the new lead claims it. Changing a CLI owner string does not supply permission or demonstrate that the old process stopped. A deliberately released run may still contain running children; the new lead must reconcile those observations before another writer starts.

## CLI

Commands require an explicit state path. The examples use `state.json` as shorthand for the canonical path; use the actual absolute path in a real run. JSON events may come from a file or stdin. All operations are local.

```sh
python3 <skill-dir>/scripts/run_state.py init state.json --run-id run-123 --repository owner/repo --issue owner/repo#42
python3 <skill-dir>/scripts/run_state.py apply state.json --owner lead-session-123 --event - <<'JSON'
{"type":"claim"}
JSON
python3 <skill-dir>/scripts/run_state.py status state.json
python3 <skill-dir>/scripts/run_state.py resume state.json --markdown
python3 <skill-dir>/scripts/run_state.py validate state.json
```

`resume` is a read-only status view, not automatic recovery or dispatch. A Markdown summary is generated from canonical JSON; do not maintain it independently. `apply --expected-revision N` rejects a stale update before changing the file. A rejected event, invalid state, owner conflict, or lock conflict exits 2. Failed writes preserve the old state when replacement has not completed; the helper cleans its own temporary file. A crash may leave a lock requiring the reconciliation above.

Supported events:

- `context`: `values` is an object for run scope, source snapshots, branch/PR identities, approval references, budgets, baseline evidence, and next safe action. Merge updates into existing context. Record the source and scope of authorization rather than treating this field as authorization itself.
- `add-step`: unique `step`, full hexadecimal `base` commit ID, canonical absolute `checkout`, and optional `dependencies` naming existing step IDs. Dependency cycles and unknown IDs are rejected. Declare prerequisites before dependents. Active steps cannot share the same recorded checkout or runtime task ID; the lead must resolve path aliases and actual file/resource ownership before recording them.
- `transition`: `step` and `to`. Starting a pending/rework step requires a new `attempt_id`; include the actual `task_id` for a delegated attempt, or omit it for direct lead work. A waiting step resumes the same attempt. Dependencies must be accepted or integrated, and the lead must separately establish that their code is in the chosen base/checkout.
- `followup`: stable `id` and `values`, merged without dropping prior fields. New items default to `awaiting-answer` and require `problem`, discovery `evidence`, and `pending_question`. Also retain location/symbol, discovery source, base presence/evidence or unknown, deferral reason, tracker classification/evidence, recommendation, source PR, decision, and outcome as they become known. These extra facts can be fields in `values`.
- `release`: clears the recorded owner; it does not cancel anything.

States: pending → running ↔ waiting → verifying → accepted → integrated. `rework`, `blocked`, and `cancelled` are explicit dispositions; the helper rejects invalid jumps. Rework requires a fresh attempt ID, blocked work can return to pending after reconciliation, and integrated/cancelled states are terminal. Reasons are required for rework/block/cancel.

When a delegated running/waiting attempt leaves those states, supply `terminal_status` (`completed`, `failed`, `cancelled`, or `interrupted`) and `terminal_evidence` from an actual host observation. A child claiming completion, a wait timeout, or merely requesting cancellation is not such evidence. The helper checks that an observation is recorded, not whether it is true; the lead must inspect the host. Do not record a timeout or pending question as terminal. Direct lead attempts have no child task to terminate.

Acceptance requires `head` and a non-empty `evidence` list from independent lead verification on that artifact. Include commands/observations, result, relevant environment, acceptance IDs, and limitations. Integration requires the exact accepted `source_head` and the resulting integrated `head` (which can differ after cherry-pick). Reintegrating the same source, reusing an integration head, or replaying an integrated step is rejected. Git ancestry, current HEAD, worktree contents, and remote publication must still be independently checked.

Example acceptance event, after a genuine observed check:

```json
{
  "type": "transition",
  "step": "S1",
  "to": "accepted",
  "head": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "evidence": ["C1: fixture comparison at this head passed; command, cwd and exit recorded in checks/S1.txt; native UI not exercised"]
}
```

Follow-up outcomes are `awaiting-answer`, `fixed`, `tracked`, `added`, `opened`, or `dropped`. `tracked` requires actual tracking evidence. `added`/`opened` require both a recorded authorization reference and a verified tracker destination; `dropped` requires the user's decision. A proposed destination or unanswered question is not permission or coverage. Status retains unanswered follow-ups across process restarts. Recheck coverage and raise retained pending decisions on resume.

## Environments without Python

Keep the same canonical facts, explicit ownership, artifact checks, transitions, and retained follow-ups using the host's available local storage mechanism. Disclose that executable validation is unavailable. Do not invent a tool, claim that an unrun validator passed, or introduce a provider requirement. Preserve the existing run ledger if migrating; reconcile its actual tasks, Git state and evidence before creating canonical JSON, and keep older artifacts as referenced evidence rather than conflicting writable state.
