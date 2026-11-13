---
name: research
license: MIT
description: Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent.
---

Investigate directly by default. If the user requests delegation and the host supports it, use a fresh-context research agent through the host's native delegation mechanism. Do not require background-agent support.

Research workflow:

1. Investigate the question against **primary sources** (official docs, source code, specs, first-party APIs), not a secondary write-up of them. Follow every claim back to the source that owns it.
2. Write the findings to a single Markdown file, citing each claim's source.
3. Save it where the repo already keeps such notes; match the existing convention, and if there is none, put it somewhere sensible and say where.

Separate verified findings, inference, and unresolved questions. Record the research date for changeable facts. If browsing or a source is unavailable, state the gap rather than treating recollection as verification. Keep credentials and private source content out of notes intended for sharing.
