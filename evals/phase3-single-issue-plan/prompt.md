---
tags: [skill-creator]
max_turns: 60
timeout_seconds: 1800
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash, Agent]
---

Create a plan to implement Phase 3. After implementing the plan, break the plan up into steps give hand off to a scoped sub agent using opus 5.5 medium. Each agent can then work on that step, you verify it, ask for more changes or commit it and then repeat with a new sub agent. Once all the issue work is complete you will open a new PR.

Issue link: https://github.com/JamalLyons/bot-automation/issues/4
