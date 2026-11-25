# Follow-ups and the ledger

Read when recording a deferred item, before tracker reconciliation and the follow-up question, before any approved issue creation or edit, and when writing the final report.

## Recording

Whenever the lead decides not to fix a discovered problem, immediately record a stable item ID, problem, file/symbol, discovery source (reviewer, child report, or lead verification), base-branch presence with evidence or unknown, and reason for leaving it out of this PR. Include pre-existing bugs, behavior verified only by unit tests, and gaps assigned to later tasks. Persist each item's tracker classification/evidence, recommendation, source PR, pending question, user authorization, and outcome; a mention in chat is not the ledger.

## Tracker reconciliation and the question

Before the final report, check every unfixed ledger item against the repository's open issues (with pagination) and, for an epic task, its sibling tasks. Classify it as tracked only when an existing issue's scope or acceptance criteria require the fix; cite the issue and quote the covering line. Partly tracked means an issue touches the area but could close with the problem still present; otherwise it is untracked. File ownership alone is not coverage. If tracker access is unavailable, record the limitation and treat coverage as unverified, not tracked. Include each unfixed item and its tracking evidence, or “not yet tracked,” in the PR body; refresh it after reconciliation and any approved follow-up.

After the relevant PRs are open and before the final report, present all partly tracked or untracked items together, with one recommendation each: fix now in this PR, add to a named existing issue as a scope line plus an acceptance criterion, open a new issue, or drop with a stated reason. Ask once per run using the host's question tool when available; otherwise ask a plain question in the final message. Batch across the queue rather than ask per item, and continue the next approved issue while an answer is pending. The question must not hold up approved implementation or PR creation. No answer is not approval, including for a recommended fix or drop.

Act only on the user's answer within the approved items and destinations; scope rules and correction budgets still apply.

## Follow-up issues belong to the epic

When a recommendation is to open a new issue, name its parent in the question: the epic of the source issue (the epic this run expanded, or the source issue's parent from `GET /repos/{o}/{r}/issues/{n}/parent`). Say plainly "open as a sub-issue of #E" so the user's approval covers creation and linking together. If the source issue has no parent, say so and offer the source issue itself as the parent, or no parent, and follow the user's answer. Never file a follow-up as a loose, unlinked issue when a parent exists.

For each approved new issue under an epic:

1. Before creating it, re-check the epic's sub-issues and open issues for an equivalent item, so a re-run does not duplicate it.
2. Create it with the epic's label (the label its sibling tasks carry, if any) and a body that starts with `Part of #E. Found while working on #n in <PR link>.`, followed by Scope, Acceptance criteria, and Verification sections so the next workforce run can plan it. Do not add an active `<!-- workforce-epic: ... -->` marker; that marker belongs to `create-workforce-epic`.
3. Link it: `POST /repos/{o}/{r}/issues/{E}/sub_issues` with `sub_issue_id` set to the new issue's integer `id` (not its number). Never send `replace_parent`. Add a blocked-by dependency only if the user approved one.
4. Verify with `GET /repos/{o}/{r}/issues/{new}/parent`. If linking fails (other owner, sub-issue limit, endpoint unavailable), keep the created issue, report the failure with the error, and record it in the ledger. Do not retry by creating another issue.
5. Record the new issue number, parent, and link result in the ledger and the PR's Outstanding items, and list it as "opened as #new under epic #E" in the final report.

The same rule applies to tasks a child or reviewer suggests: they are ledger items that follow this flow, not issues a child may create. Before an approved issue edit, reread the body and preserve it, including any `<!-- workforce-epic: ... -->` marker. Append to its scope and acceptance sections (add those sections if absent), rather than rewriting existing text, and name the source PR. Verify authorized mutations and record issue links and outcomes in the ledger.

## Final report

List every discovered item with its outcome: fixed, tracked in #n (already), added to #n, opened as #n, dropped by the user, or still awaiting the user's answer. For unanswered partly tracked/untracked items, explicitly say “untracked” (including any partial coverage or access limitation), retain them in the ledger, and state the pending decision even in non-interactive runs. Never silently drop an item or describe a proposed destination as existing coverage.
