---
name: research
license: MIT
description: Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent.
---

Investigate directly by default. If the user requests delegation and the host supports it, use a fresh-context research agent through the host's native delegation mechanism. Do not require background-agent support.

## Output mode

- **Answer inline** only when the user asks a quick question or says not to save a file. Still label confidence and cite sources.
- **Otherwise save a file** using [references/report-template.md](references/report-template.md).
- File location and name: match the repo's existing convention (check `docs/research/`, `docs/notes/`, `notes/`, and ADR folders such as `docs/adr/`). If none exists, use `docs/research/research-<yyyy-mm-dd>-<topic-slug>.md`. Report the path.

## Source ranking

1. Spec or source code at a pinned revision.
2. Official docs for the matching product version.
3. Maintainer statements, release notes, changelogs.
4. Everything else (blogs, forums, answers, summaries, recollection). Never sufficient alone for **Verified**.

Match the version or revision the user's project actually uses. Follow consequential claims back to the source that owns them. When sources conflict, prefer the higher rank for the matching version and record the conflict.

## Workflow

1. State the scoped question from the request and repository context.
2. Gather evidence in ranking order. Label each finding **Verified**, **Likely**, or **Unverified** as defined in the template.
3. Record the research date and each source's version, revision, or date. Distinguish cached evidence from live verification.
4. Write the bottom-line answer first, then findings, conflicts, and open questions.

## Budget and stopping

- Stop once the scoped question is answered with primary evidence.
- Stop after about 5 source hops without new relevant evidence, or when progress needs unavailable evidence (no browsing, missing source). Report the gap as an open question; do not fill it from recollection.
- Do not expand into adjacent topics merely because more sources exist.

## Rules

- Separate verified findings from inference; never invent citations.
- Keep credentials, tokens, and private source content out of notes intended for sharing.
