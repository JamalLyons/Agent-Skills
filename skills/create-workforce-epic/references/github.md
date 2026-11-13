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
- Two issues with the same marker key stop the run, including closed issues. Choosing a canonical issue and changing marker identity requires explicit authorization; see Duplicate-marker recovery below.
- When the dependencies endpoint returns 404 or 410 (feature unavailable on the host), `apply` warns and continues. Blockers are then recorded only in each body's Dependencies line, and `epic_status.py` cannot see them.
- Sub-issues are required (user decision). A host without them fails at the first sub-issue read with a clear error.

## Duplicate-marker recovery

Closing an extra issue does **not** resolve duplicate identity: discovery includes `state=all`, and linked sub-issues are also searched. Removing a label alone is insufficient for a linked task. The script never chooses a winner or edits markers automatically.

1. Stop the run and list every matching issue number and marker. Ask the user to choose the canonical issue and authorize the exact issue-body edits if that authority has not already been given. Preserve the plan's key; changing it would describe a different epic or task.
2. Leave the canonical marker intact. In each explicitly superseded issue, rename **only the marker prefix**, preserving its JSON payload and the rest of the body:
   - Task: `<!-- workforce-epic: {...} -->` becomes `<!-- workforce-epic-superseded: {...} -->`.
   - Epic: `<!-- workforce-epic-root: {...} -->` becomes `<!-- workforce-epic-root-superseded: {...} -->`.
3. Add a short human-readable note naming the canonical issue (for example, `Superseded by #42`) when authorized. Retain the inactive marker as history. Closing, detaching, relabeling, or changing dependencies is a separate action requiring its own applicable authorization; it is not necessary for marker disambiguation. A superseded task still linked to the epic will be reported by status as an unmanaged task, so disclose it rather than hiding it.
4. Re-run validation and the same `apply` command **without** `--execute`. Confirm it reuses the selected canonical issue and does not propose creating a replacement. An epic selected for reuse must still be open. Only resume writes within the user's existing approved scope after inspecting that dry run.

The inactive prefixes above are not matched as active markers. Do not retain a second active copy elsewhere in the body, remove user text, or change an unrelated issue to bypass the conflict. A user may perform these edits directly; this planning skill's ordinary apply operation remains create/link-only.

## Scope reconciliation

Reusing a marker does not apply an updated local plan to an existing issue body. Before **any** write, `apply` compares each reused task's generated sections, title, and marker metadata with the rendered plan. When the plan retains a new-epic object, its matched root body/title are compared too. A numbered epic has no proposed summary/background, so root-body comparison is unavailable in that mode; task scope is still checked.

Drift stops both dry-run and execute with exit 2. The JSON report contains `scope_reconciled: false` and `drift` entries identifying task/issue and exact `current`/`proposed` section values. Text output includes unified diffs. No body is edited and no label, issue, link, or dependency is created before this check passes.

Choose a disposition rather than bypassing the check:

1. **Keep the current issue scope:** align the local plan with the current managed sections after confirming that is the intended scope. Do not claim the rejected additions were applied.
2. **Change the issue scope:** obtain or honor authorization for the exact issue edits, preserve the active marker and unrelated human text, and make those edits separately from this create/link-only skill. Present the proposed section changes for review. Re-run validation and a non-executing apply; continue approved creation/linking only after it reports reconciled scope.

Comparison ignores trailing whitespace/line endings, active-marker JSON formatting, and acceptance checkbox completion state. It resolves task-key blockers to discovered issue numbers before comparing dependencies. Custom headings present in the proposed generated content are compared too; unknown interior sections are treated conservatively. Trailing unknown human sections are left alone. If removing a trailing custom heading from an old plan field, inspect the complete body diff: historical bodies do not record ownership of arbitrary extra sections. No issue body, including ignored human sections, is rewritten by apply.

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
