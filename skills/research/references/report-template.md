# Research report template

Copy this structure. Omit a section only when it would be empty, and say "None" for empty Conflicts or Open questions rather than deleting them.

```markdown
# <Topic>

- **Question:** <the scoped question, one sentence>
- **Date:** <yyyy-mm-dd research date>
- **Scope:** <product/version/revision covered; what was excluded>

## Answer

<2–4 sentences. The direct answer, its confidence, and the main limit.>

## Findings

1. **[Verified]** <claim> — [source](<url>) (<version, revision, or date>)
2. **[Likely]** <claim> — inferred from [source](<url>); <why the inference holds>
3. **[Unverified]** <claim> — <secondary source or recollection>; <what would verify it>

## Conflicts

- <source A says X; source B says Y; which applies and why, or "unresolved">

## Open questions

- <what remains unknown and what evidence would settle it>

## Sources

- <title> — <url> — <version/revision> — accessed <yyyy-mm-dd> (<live | cached copy captured yyyy-mm-dd>)
```

## Confidence labels

- **Verified**: confirmed directly against a primary source (spec, source code, official docs, first-party API) at a stated version, revision, or date.
- **Likely**: inferred from primary evidence, but no primary source states it directly. Say what the inference rests on.
- **Unverified**: supported only by secondary sources (blogs, forums, answers, AI summaries) or recollection. Never present as fact.

Label every finding. A cached copy can support Verified for the captured version and date, but say it was not re-checked live.
