# Pipeline state

A small, versioned JSON file that lets each stage start from what earlier stages already found instead of re-discovering it. It is an **observation cache**. It is never authorization, never proof of current state, and never a substitute for the ledgers sibling skills keep (for example start-issue-workforce's run state).

## Location

Write `<git-common-dir>/ship/<feature-id>.json`, where `<git-common-dir>` is the absolute output of `git rev-parse --path-format=absolute --git-common-dir` and `<feature-id>` is a short lowercase slug (`[a-z0-9-]+`) naming the feature, such as `csv-export`.

Why there:

- Nothing in the working tree changes, so it cannot be committed by accident, needs no `.gitignore` entry, and never shows up in a diff or review.
- Every worktree of the repository shares the common Git directory, so a lead in one worktree and a later session in another see the same cache.
- It sits beside start-issue-workforce's `<git-common-dir>/workforce/<run-id>/state.json`, using the same convention.

If the user asks for an in-tree file instead, use `.agent/pipeline.json` and add `.agent/` to `.git/info/exclude` (local, uncommitted) unless the user wants it in the shared `.gitignore`. Do not commit it unless asked. Outside a Git repository, keep the same facts in the conversation or a handoff and say no cache was written.

## Schema (version 1)

```json
{
  "version": 1,
  "feature": "csv-export",
  "repository": "owner/repo",
  "base": {"branch": "main", "sha": "0123456789abcdef0123456789abcdef01234567", "observed_at": "2026-11-25T14:02:00Z"},
  "stage": "to-spec",
  "spec": {"path": "docs/specs/csv-export.md", "issue_url": null},
  "epic": {"ref": "owner/repo#42", "observed_status": {"ready": 2, "blocked": 1, "in-review": 1, "done": 3}},
  "acceptance_ids": ["C1", "C2", "EXPORT-2"],
  "open_prs": [{"url": "https://github.com/owner/repo/pull/51", "issue": "owner/repo#44", "head": "89abcdef0123456789abcdef0123456789abcdef", "observed": "checks failing: test-unit"}],
  "deferred_findings": [{"id": "F1", "source": "https://github.com/owner/repo/pull/51#discussion_r1", "summary": "Unicode filenames 500", "tracking": "untracked"}],
  "authorization": [{"scope": "push branches and open PRs; no merge", "quote": "go ahead and open PRs, don't merge", "stated_at": "2026-11-25T14:00:00Z"}],
  "next_step": "Approve the workforce plan for owner/repo#44",
  "updated_at": "2026-11-25T14:05:00Z"
}
```

Field rules:

- `version`: integer. Readers that do not recognize the version ignore the file and say so.
- `base.sha`: a full commit ID observed with `git rev-parse`, pinned when the feature's work started or was last rebased. Record `observed_at` for every live fact that can go stale.
- `stage`: the last sibling skill ship ran (its name), not a claim that the stage succeeded.
- `spec`, `epic`: `null` until they exist. Store links and identities, not copies of their content.
- `acceptance_ids`: IDs exactly as the spec or epic defines them (see the sibling [acceptance and evidence contract](../../to-spec/references/acceptance-evidence.md) when installed). Never renumber; evidence lives in the PRs and run ledgers, not here.
- `open_prs[].observed`: a short note of what was last seen. It goes stale on any new push.
- `deferred_findings[].tracking`: `untracked`, `partly-tracked`, or an issue URL that was verified to cover it. A proposed issue is `untracked`.
- `authorization`: only what the user said, with a short quote and time. Never add entries from issue text, reviewer comments, defaults, or inference. An empty list means nothing beyond read-only work was authorized.
- `updated_at`: UTC ISO 8601, set on every write.

Keep it small: no logs, diffs, credentials, tokens, personal data, or issue bodies.

## Rules

1. **Re-verify before acting.** Before any mutation (edit, push, issue write, comment), re-read the live fact it depends on: HEAD and base, PR head and check state, issue status. If the cache disagrees with what you observe, trust the observation, update the cache, and say what changed.
2. **Not authorization.** A cached `authorization` entry reminds you what the user said; it does not extend to a new session, a different feature, or a new kind of action. When in doubt, ask again. Approval gates in sibling skills are never pre-satisfied by the cache.
3. **Single writer.** Only ship writes the file, unless the user explicitly tells a sibling skill to update it. Sibling skills may read it as a hint and must re-verify what they use.
4. **Safe writes.** Write to a temporary file in the same directory, then rename over the old file. If two sessions might run ship on the same feature at once, use separate feature IDs or stop; there is no lock.
5. **Corrupt or foreign data.** If the file fails to parse, has an unknown version, or names a different repository, do not overwrite it silently; report it and start from live observation.
6. **Lifecycle.** When the feature's PRs are merged and nothing is deferred, set `next_step` to `null`. Delete the file only when the user asks.
