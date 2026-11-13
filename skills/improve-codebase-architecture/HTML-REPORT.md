# Architecture report

Use the host's supported artifact format and rendering requirements. For a standalone HTML fallback, write a single offline file in the OS temporary directory. Use inline CSS and SVG; no CDN, build tool, server, or external font is required. Escape code identifiers, paths, and repository text before inserting them into HTML. Keep that fallback static, with no scripts or event handlers.

Use a readable maximum width, generous spacing, responsive before/after columns, and labels that make sense without color. Each candidate is an article with:

- A short title naming the deepening opportunity.
- A recommendation badge: Strong, Worth exploring, or Speculative.
- The affected file paths and a concrete costly change, defect, or code path establishing friction. Distinguish observed evidence from inferred benefit and state confidence or missing evidence.
- A before/after diagram showing modules, interfaces, seams, and dependency flow.
- A short problem, proposed change, and expected gains in locality, leverage, and test coverage.
- Qualitative effort and migration risk, the first independently verifiable step, and behavior/regression coverage that must survive. Explain why this is preferable to leaving the structure alone.
- Any conflict with an existing ADR, including why reopening that decision may be justified.

Choose the diagram that explains the actual change: boxes and arrows for dependencies, horizontal bands for shallow layers, nested boxes for call-graph collapse, or interface/implementation rectangles for depth. Provide text labels or a caption so the diagram is understandable with assistive technology. Use domain names from the project's glossary when present, and architectural terms from [codebase-design](../codebase-design/SKILL.md).

Finish with the top recommendation and the evidence for prioritizing it over its cost and risk. `Strong` needs concrete evidence and a credible migration path; speculative candidates state what would resolve uncertainty. Do not fabricate candidates to fill a quota; a report with no justified refactor is valid. Present it through the host's artifact support, return a file link when rendering is unavailable, or use text when no file output is supported. Keep a durable decision summary only when requested or already authorized; follow the repository's established location.
