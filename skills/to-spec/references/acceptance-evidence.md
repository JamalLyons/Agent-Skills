# Acceptance and evidence

Use this small contract when a specification becomes tasks, changes, verification, or review. Adapt its presentation to the repository and the host's tools; it does not require a particular tracker, provider, agent, or file format.

## Requirement identity

- Preserve existing source IDs and their meanings. If none exist, assign stable IDs such as `C1`, `C2` to the agreed criteria. State the source document or issue when IDs could be ambiguous.
- Keep IDs through task decomposition, reordering, and review. Several tasks may implement one criterion, and one task may cover several criteria. Link them rather than renumbering the source.
- Do not reuse a retired ID for different behavior. Mark a changed or superseded requirement and its replacement explicitly. If a destination schema requires another ID format, retain a source-ID-to-local-ID mapping.
- An agreed criterion states observable behavior under relevant preconditions. Proposed behavior, uncertain interpretation, and missing product decisions stay labeled as proposals or blockers. Include failure paths and edge cases only when supported by the agreed scope or an established existing contract.

## Delivery record

For each acceptance ID, retain these facts as they become available:

1. **Requirement:** source, agreed behavior, and relevant preconditions or expected failure outcome.
2. **Work:** task/issue and implementation artifact or change that claims to fulfill it. Before implementation these are planned links, not evidence of completion.
3. **Verification:** planned check or actual observed evidence, clearly distinguished. For an executed check, record its command or observation, result, relevant revision/artifact, and material environment assumptions. An inspected implementation can be evidence, but state what inspection cannot establish.
4. **Limit:** remaining coverage gap, failed/unavailable check, unresolved dependency, or human action. Keep incomplete criteria visibly incomplete.

For example, if the agreed requirement is `EXPORT-2 — an export preserves the existing column order`, the record might link its implementation task, the actual fixture comparison on a named revision, and the limitation that a different export format was not in scope. Do not add a new format or declare a test passed to complete the record.

During spec synthesis, provide agreed criteria and planned verification only, except where real evidence is already available. During delivery and review, update the same IDs with observed results. A child report, an implemented-looking task, or a proposed test does not by itself establish acceptance. When evidence conflicts with a completion claim, report the discrepancy and retain the limitation.
