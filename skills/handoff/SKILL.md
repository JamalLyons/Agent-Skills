---
name: handoff
license: MIT
description: Compact the current conversation into a handoff document for another agent to pick up.
---

Write a handoff document summarising the current conversation so a fresh agent can continue the work. By default save a uniquely named file, such as `handoff-<timestamp>-<random>.md`, in the user's OS temporary directory (`$TMPDIR`, else `/tmp`; `%TEMP%` on Windows), using exclusive creation or the host's unique-file mechanism. Do not overwrite another handoff. Use a durable project location only when the user requests one, following the repository's convention.

Include a "suggested skills" section in the document, naming relevant available skills and their repository-relative paths or installation names. The next agent can load them using its host's skill mechanism or read their SKILL.md files directly.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.

Capture the objective, user constraints and authorization, completed work, exact next steps, blockers, and validation results with limitations. Include:

- Repository/worktree path, branch and observed HEAD when relevant, plus staged, unstaged, and untracked work that must be preserved.
- Authoritative artifact paths or URLs and check commands/results tied to the revision or worktree state actually observed; distinguish checks not run from failures.
- Active background/delegated work: host/task or process identity, checkout, last observed status, and how the next agent can reconcile it. A timeout does not establish termination; do not imply that tool sessions transfer to the new agent.
- The exact next command when it is known and safe within existing authorization; otherwise state the missing decision or evidence instead of inventing an executable step.

Clearly distinguish observations from assumptions and note when the state was observed. Tell the next agent to recheck Git, active work, remote state, and authorization scope before mutations; a handoff snapshot is not proof of current state or new permission. End with a clickable Markdown link to the handoff file's absolute path.
