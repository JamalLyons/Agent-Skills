---
name: handoff
license: MIT
description: Compact the current conversation into a handoff document for another agent to pick up.
---

Write a handoff document summarising the current conversation so a fresh agent can continue the work. Save to the temporary directory of the user's OS (`$TMPDIR`, else `/tmp`; `%TEMP%` on Windows) - not the current workspace.

Include a "suggested skills" section in the document, naming relevant available skills and their repository-relative paths or installation names. The next agent can load them using its host's skill mechanism or read their SKILL.md files directly.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.

Capture the objective, user constraints and authorization, completed work, exact next steps, blockers, and validation results with limitations. Include the repository path, branch and HEAD when relevant, and uncommitted work that must be preserved. Clearly distinguish observed state from assumptions. End by giving the user the handoff file's absolute path.
