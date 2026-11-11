# Workforce skills

Claude Code skills for handing GitHub work to a team of agents. GitHub issues are the queue.

| Skill | What it does |
|-------|--------------|
| [`start-issue-workforce`](skills/start-issue-workforce/) | Turns one or more GitHub issues into verified pull requests through scoped sub-agents and usage-aware model routing. |
| `create-workforce-epic` *(planned)* | Breaks a large issue into PR-sized sub-issues with dependencies, ready for `start-issue-workforce` to pick up. |

## Install

```bash
git clone https://github.com/JamalLyons/issue-workforce-skill ~/.claude/skills/issue-workforce-skill
~/.claude/skills/issue-workforce-skill/install.sh
```

Claude Code only discovers skills one level deep (`~/.claude/skills/<name>/SKILL.md`), so `install.sh` symlinks each folder in `skills/` into `~/.claude/skills/`. It is idempotent. Re-run it after pulling when a skill is added or renamed; it also removes broken links left behind by renamed or deleted skills from this repo. Set `CLAUDE_SKILLS_DIR` to install somewhere else.

## Layout

```
install.sh                     symlinks skills/* into ~/.claude/skills
skills/start-issue-workforce/  SKILL.md, config, references, scripts, tests, evals
```

Each skill is self-contained: its scripts resolve paths relative to its own folder.

## Validation

```bash
cd skills/start-issue-workforce && python3 -B -m unittest discover -s tests -v && bash -n scripts/detect_checks.sh
```
