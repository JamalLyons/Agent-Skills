# PR body

Use `Closes #<n>` only for fully fulfilled acceptance with required evidence; otherwise `Part of #<n>`.

```markdown
<Closes or Part of issue references>

## Summary
<Concrete problem and resulting behavior>

## Changes
- <coherent step and accepted commit SHA>

## Acceptance
- [x] <stable criterion ID, behavior, observed evidence tied to the verified artifact>
- [ ] <stable criterion ID; deferred/needs human; exact remaining action and evidence limitation>

## Verification
- <command>: <actual outcome, relevant evidence>
- <unavailable/not run check and reason; practical limitation>

## Outstanding items
- <ledger item ID, problem and file/symbol>: <opened as #n under epic #E, tracked in #n with covering scope/acceptance line, or not yet tracked; include partial coverage and pending recommendation/decision>

## Review notes
<Material decisions, unresolved concerns, actual stacked PR base if applicable>
```

Omit empty sections. Never pre-fill pass marks, invent manual testing, or imply approval/merge. Partial work with unresolved required checks must be an authorized draft and explicitly identified. Use actual PR base/head for the change summary. Publish via a body file; after an ambiguous API result look for the existing PR before retrying. Link immediately through the host's tool after creation/update/push when available; otherwise return the PR URL. List every discovered item left unfixed under Outstanding items, including pre-existing defects and verification gaps. File ownership or a proposed destination is not tracking; say “not yet tracked” until required scope/acceptance coverage is confirmed. Refresh after tracker reconciliation and approved follow-up. Never create, edit, or comment on issues without the user's authorization for the specific items and destinations (see section 5 of the skill).
