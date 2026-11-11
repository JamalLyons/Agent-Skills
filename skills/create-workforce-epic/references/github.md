# GitHub behaviour

Checked against docs.github.com and the live GraphQL schema on 2026-11-10.

## Endpoints used

| Purpose | Call | Notes |
|---|---|---|
| Read epic / external blocker | `GET /repos/{o}/{r}/issues/{n}` | A `pull_request` key means it is a PR, which is rejected |
| Find existing tasks | `GET /repos/{o}/{r}/issues/{epic}/sub_issues` and `GET /repos/{o}/{r}/issues?state=all&labels={label}` | Paginated at 100. Matched by hidden marker, not by title |
| Label | `GET` / `POST /repos/{o}/{r}/labels` | Created only when missing |
| Create new epic | `POST /repos/{o}/{r}/issues` with `title`, `body`, `labels` | Only when the plan's `epic` is an object and no labelled issue carries its root marker |
| Create task | `POST /repos/{o}/{r}/issues` with `title`, `body`, `labels` | The label is set at creation, so an interrupted run can find the issue again |
| Link sub-issue | `POST /repos/{o}/{r}/issues/{epic}/sub_issues` with `sub_issue_id` | **Integer `id`**, not `number`. The sub-issue must belong to the same owner. `replace_parent` is never sent |
| Check parent after a 422 | `GET /repos/{o}/{r}/issues/{n}/parent` | Another parent → stop (exit 2) |
| Dependencies | `GET` / `POST /repos/{o}/{r}/issues/{n}/dependencies/blocked_by` with `issue_id` | **Integer `id`** of the blocking issue |
| Status | GraphQL `Issue.subIssues`, `blockedBy`, `closedByPullRequestsReferences`, `ClosedEvent.closer` | One paginated query in `epic_status.py` |

All writes produce content, and GitHub may apply secondary rate limits to fast content creation. `apply` waits one second between writes (`--delay`).

## Idempotency and failures

- Each task body carries `<!-- workforce-epic: {...} -->` with the epic reference and task key. Before writing, `apply` collects every issue under the epic and every issue with the plan label, then matches markers. Keys already present are reused and never edited.
- A new epic carries `<!-- workforce-epic-root: {"v":1,"key":...} -->` and the plan label. Before creating it, `apply` looks for a labelled issue with that root key and reuses it; two matches stop the run, and a closed match stops it too.
- A create whose response is lost (timeout, reset) may still have succeeded. Re-running finds it by label and marker and continues with linking and dependencies.
- Two issues with the same marker key stop the run. A person decides which to close.
- When the dependencies endpoint returns 404 or 410 (feature unavailable on the host), `apply` warns and continues. Blockers are then recorded only in each body's Dependencies line, and `epic_status.py` cannot see them.
- Sub-issues are required (user decision). A host without them fails at the first sub-issue read with a clear error.

## Status semantics (`epic_status.py`)

| Status | Meaning |
|---|---|
| `ready` | Open agent task; every blocker is satisfied |
| `blocked` | A blocker is open, or was dropped (closed as not planned or duplicate: re-plan needed) |
| `check` | A blocker was closed as completed without a merged PR or commit; confirm the work is really in the default branch |
| `in-review` | An open PR references the task as closing it |
| `human` | Open human task |
| `done` | Closed as completed by a merged PR or a commit, or a human task closed as completed |
| `done-unverified` | Closed as completed with no merged PR or commit found |
| `dropped` | Closed as not planned or duplicate |

A blocker is satisfied only when it is `done`. `--ready` prints ready issue numbers in dependency order, one per line, and `--json` gives the full structure. Sub-issues without a marker are included as agent tasks with unknown tier.

## Limits

GitHub limits sub-issues per parent and nesting depth. The script caps a plan at 50 tasks and suggests phases above 15. Blockers in another repository appear in status by their full reference but are not created or linked by `apply`, which only accepts same-repo `"#n"` blockers.
