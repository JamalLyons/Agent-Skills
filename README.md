# Workforce skills

Claude Code skills for handing GitHub work to a team of agents. GitHub issues are the queue.

| Skill | What it does |
|-------|--------------|
| [`issue-workforce`](skills/issue-workforce/) | Turns one or more GitHub issues into verified pull requests through scoped sub-agents and usage-aware model routing. |
| `create-workforce-epic` *(planned)* | Breaks a large issue into PR-sized sub-issues with dependencies, ready for `issue-workforce` to pick up. |

## Install

```bash
git clone --branch main https://github.com/JamalLyons/issue-workforce-skill ~/.claude/skills/issue-workforce-skill
~/.claude/skills/issue-workforce-skill/install.sh
```

Claude Code only discovers skills one level deep (`~/.claude/skills/<name>/SKILL.md`), so `install.sh` symlinks each folder in `skills/` into `~/.claude/skills/`. It is idempotent. Re-run it after pulling when a new skill is added. Set `CLAUDE_SKILLS_DIR` to install somewhere else.

## Layout

```
install.sh                 symlinks skills/* into ~/.claude/skills
skills/issue-workforce/    SKILL.md, config, references, scripts, tests, evals
```

Each skill is self-contained: its scripts resolve paths relative to its own folder.

## Validation

```bash
cd skills/issue-workforce && python3 -B -m unittest discover -s tests -v && bash -n scripts/detect_checks.sh
```
