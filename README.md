# Agent skills

A shared collection of [Agent Skills](https://agentskills.io) for Claude Code, Codex, Cursor, and Gemini CLI. Keep the skills here, edit them once, and use them across agents.

## Install

```bash
git clone https://github.com/JamalLyons/Agent-Skills
cd Agent-Skills
./install.sh
```

The installer links each skill into `~/.claude/skills` and `~/.agents/skills`. Start a new agent session to load them.

Keep the clone in place: installed skills point to it. After pulling new skills or moving the clone, run `./install.sh` again. Existing directories are preserved.

To install somewhere else, use `./install.sh --target /path/to/skills` (repeatable).

## Skills

### Plan and explore

- [grill-me](skills/grill-me/SKILL.md) — Challenge a plan and resolve assumptions.
- [research](skills/research/SKILL.md) — Investigate primary sources and save cited findings.
- [to-spec](skills/to-spec/SKILL.md) — Turn a conversation into an implementation spec.
- [domain-modeling](skills/domain-modeling/SKILL.md) — Define domain terms and record architectural decisions.
- [codebase-design](skills/codebase-design/SKILL.md) — Design modules with small interfaces and useful behavior.
- [improve-codebase-architecture](skills/improve-codebase-architecture/SKILL.md) — Find and explain worthwhile architectural changes.

### Build and deliver

- [tdd](skills/tdd/SKILL.md) — Build behavior through failing tests and small implementation steps.
- [code-review](skills/code-review/SKILL.md) — Review changes against project standards and the spec.
- [wizard](skills/wizard/SKILL.md) — Generate an interactive script for manual setup steps.
- [handoff](skills/handoff/SKILL.md) — Prepare a fresh agent to continue the work.
- [create-workforce-epic](skills/create-workforce-epic/SKILL.md) — Break a GitHub epic into scoped, dependent issues.
- [start-issue-workforce](skills/start-issue-workforce/SKILL.md) — Take GitHub issues through implementation, verification, and pull requests.

## Use

Ask your agent to use a skill by name, or select it through the agent's skill menu. For example:

> Use grill-me to stress-test this plan.
>
> Use code-review to review this branch against main.

Each folder in `skills/` contains its instructions in `SKILL.md`, plus any supporting files. Available tools and permissions depend on the agent running it.

## Credits

Ten skills are adapted from [Matt Pocock's skills](https://github.com/mattpocock/skills). Source revisions, changes, and MIT license details are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
