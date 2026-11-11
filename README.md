# Workforce skills

[Agent Skills](https://agentskills.io) for handing GitHub work to a team of agents. GitHub issues are the queue. They work in Claude Code, Codex, Cursor, and Gemini CLI.

| Skill | What it does |
|-------|--------------|
| [`start-issue-workforce`](skills/start-issue-workforce/) | Turns one or more GitHub issues into verified pull requests through scoped sub-agents and usage-aware model routing. |
| [`create-workforce-epic`](skills/create-workforce-epic/) | Breaks a large issue into PR-sized native sub-issues with blocked-by dependencies, ready for `start-issue-workforce` to pick up. |

Typical flow: *"break owner/repo#42 into a workforce epic"* → review the plan → issues are filed as sub-issues → *"start a workforce on the ready tasks of owner/repo#42"*.

## Install

```bash
git clone https://github.com/JamalLyons/agent-workforce-skills ~/.claude/skills/agent-workforce-skills
~/.claude/skills/agent-workforce-skills/install.sh
```

Agents only discover skills one level deep (`<skills-dir>/<name>/SKILL.md`), so `install.sh` symlinks each folder in `skills/` into two directories:

| Directory | Read by |
|---|---|
| `~/.claude/skills` | Claude Code (and Cursor, for compatibility) |
| `~/.agents/skills` | Codex, Cursor, and Gemini CLI (the shared Agent Skills location) |

It is idempotent. Re-run it after pulling when a skill is added or renamed; it also removes broken links left behind by renamed or deleted skills from this repo. Override the defaults with `CLAUDE_SKILLS_DIR` / `AGENT_SKILLS_DIR`, or link only into specific directories with `./install.sh --target DIR` (repeatable), for example a project's `.agents/skills`.

New skills show up in a new session: Codex usually picks changes up on its own (restart it if not), Cursor scans at startup, and Gemini CLI has `/skills reload`. Cursor reads both default directories, so it may list each skill twice.

## Layout

```
install.sh                     symlinks skills/* into ~/.claude/skills and ~/.agents/skills
skills/start-issue-workforce/  SKILL.md, config, references, scripts, tests, evals
skills/create-workforce-epic/  SKILL.md, references, scripts, tests, evals
```

Each skill's scripts resolve paths relative to its own folder, and the skills refer to each other as siblings (`<skill-dir>/../<other-skill>`), never through an agent-specific path. `start-issue-workforce` uses `create-workforce-epic`'s `epic_status.py` for epic queues when it is installed and falls back to `gh api` otherwise.

## Validation

```bash
for s in skills/*/; do (cd "$s" && python3 -B -m unittest discover -s tests) || exit 1; done
bash -n install.sh skills/start-issue-workforce/scripts/detect_checks.sh
```
