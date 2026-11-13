---
name: research
license: MIT
description: Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent.
---

Investigate directly by default. If the user requests delegation and the host supports it, use a fresh-context research agent through the host's native delegation mechanism. Do not require background-agent support.

Research workflow:

1. State the question and useful scope from the request and repository context. Investigate against **primary sources** (official docs, source code, specs, first-party APIs), not a secondary write-up of them. Follow consequential claims back to the source that owns them; match the relevant product version or source revision.
2. Write a concise conclusion and supporting findings to a single Markdown file, citing each claim's source. For changeable facts, record the research date and source version/date or revision when available; distinguish cached evidence from current verification.
3. Save it where the repo already keeps such notes; match the existing convention, and if there is none, put it somewhere sensible and say where.

Stop when the scoped question has sufficient evidence for a useful answer, or further progress needs unavailable evidence. Do not expand into adjacent topics merely because more sources exist. Separate verified findings, inference, conflicting evidence, and unresolved questions. If browsing or a source is unavailable, state the gap rather than treating recollection as verification. Keep credentials and private source content out of notes intended for sharing.
