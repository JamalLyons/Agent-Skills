# PR body

Use `Closes #<n>` only for fully fulfilled acceptance with required evidence; otherwise `Part of #<n>`.

```markdown
<Closes or Part of issue references>

## Summary
<Concrete problem and resulting behavior>

## Changes
- <coherent step and accepted commit SHA>

## Acceptance
- [x] <criterion and evidence>
- [ ] <deferred/needs human; exact remaining action>

## Verification
- <command>: <actual outcome, relevant evidence>
- <unavailable/not run check and reason; practical limitation>

## Review notes
<Material decisions, unresolved concerns, actual stacked PR base if applicable>
```

Omit empty sections. Never pre-fill pass marks, invent manual testing, or imply approval/merge. Partial work with unresolved required checks must be an authorized draft and explicitly identified. Use actual PR base/head for the change summary. Publish via a body file; after an ambiguous API result look for the existing PR before retrying. Link immediately through the host's tool after creation/update/push. Never post issue comments unless separately requested.
