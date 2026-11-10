# PR body template

```markdown
Closes #<n>            ← or "Part of #<n>" if anything is deferred

## Summary
<2-4 sentences: what this PR delivers, in user terms.>

## Changes (one commit per step)
| # | Step | Commit |
|---|------|--------|
| 1 | <step title> | <short sha> |
| 2 | ... | ... |

## Issue checklist
- [x] <issue task>: step 1
- [x] <issue task>: steps 2-3
- [ ] <issue task>: **deferred**: <why / follow-up>
- [ ] <issue task>: **needs a human**: <exactly what to do, e.g. "add a Developer ID cert to the keychain, then run `just sign`">

## Verification
- Build: ✅ `<cmd>`
- Tests: ✅ `<cmd>`: <N passed>
- Lint/format: ✅ `<cmd>`
- Manual: <anything you actually exercised, e.g. ran `localbot run "Demo" --var x=1`>

## Notes for reviewers
<design decisions, trade-offs, anything surprising found along the way; stacked-PR note if based on another branch>
```

Leave out sections that would be empty. Keep it scannable. Reviewers read the table and the checklist first.
