# Integration review

Read before requesting reviewers in section 4 and when dispositioning their findings.

For substantive work, request two fresh read-only reviewers from different eligible hard-tier providers when available and within budget; use one when availability/privacy/budget permits only one. If delegation is unavailable, perform separate direct review passes and disclose the lack of independent reviewers. For a tiny low-risk change, lead review can suffice with the reason recorded. Give reviewers the actual PR base and head SHA, issue criteria, relevant decisions, and repository access/paths. For large diffs give a file map and require complete assigned coverage rather than blindly truncating the diff.

Require findings with file/symbol, failure scenario, severity, and evidence; no edits or delegation. Deduplicate by root cause. Independently reproduce or inspect each finding; resolve disagreement with code/tests and record dispositions. Do not decide by vote. Fix confirmed defects within the correction budget, repeat affected checks, and re-review material changes. Unresolved acceptance/safety failures block a ready PR; publish partial work only as an authorized draft with limitations.
