# Workforce skills

Claude Code skills for handing GitHub work to a team of agents. GitHub issues are the queue.

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

Claude Code only discovers skills one level deep (`~/.claude/skills/<name>/SKILL.md`), so `install.sh` symlinks each folder in `skills/` into `~/.claude/skills/`. It is idempotent. Re-run it after pulling when a skill is added or renamed; it also removes broken links left behind by renamed or deleted skills from this repo. Set `CLAUDE_SKILLS_DIR` to install somewhere else.

## Layout

```
install.sh                     symlinks skills/* into ~/.claude/skills
skills/start-issue-workforce/  SKILL.md, config, references, scripts, tests, evals
skills/create-workforce-epic/  SKILL.md, references, scripts, tests, evals
```

Each skill's scripts resolve paths relative to its own folder. `start-issue-workforce` uses `create-workforce-epic`'s `epic_status.py` for epic queues when it is installed and falls back to `gh api` otherwise.

## Validation

```bash
for s in skills/*/; do (cd "$s" && python3 -B -m unittest discover -s tests) || exit 1; done
bash -n install.sh skills/start-issue-workforce/scripts/detect_checks.sh
```
