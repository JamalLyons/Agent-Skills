# Agent skills

A skills monorepo for engineering, planning, and handing GitHub work to a team of agents. The portable [Agent Skills](https://agentskills.io) folders are shared by Claude Code, Codex, Cursor, and Gemini CLI.

| Skill | What it does |
|-------|--------------|
| [`start-issue-workforce`](skills/start-issue-workforce/) | Turns one or more GitHub issues into verified pull requests through scoped sub-agents and usage-aware model routing. |
| [`create-workforce-epic`](skills/create-workforce-epic/) | Breaks a large issue into PR-sized native sub-issues with blocked-by dependencies, ready for `start-issue-workforce` to pick up. |

Typical flow: *"break owner/repo#42 into a workforce epic"* → review the plan → issues are filed as sub-issues → *"start a workforce on the ready tasks of owner/repo#42"*.

## Engineering and productivity skills

- [`improve-codebase-architecture`](skills/improve-codebase-architecture/SKILL.md): find deepening opportunities, present a visual report, and explore the chosen candidate.
- [`to-spec`](skills/to-spec/SKILL.md): turn an existing conversation into an implementation spec; publish when requested.
- [`research`](skills/research/SKILL.md): investigate primary sources and save cited findings.
- [`tdd`](skills/tdd/SKILL.md): build behavior one failing test and implementation slice at a time.
- [`domain-modeling`](skills/domain-modeling/SKILL.md): sharpen domain terminology and record meaningful architectural decisions.
- [`codebase-design`](skills/codebase-design/SKILL.md): design deep modules and compare alternative interfaces.
- [`code-review`](skills/code-review/SKILL.md): review changes against repository standards and the originating spec independently.
- [`wizard`](skills/wizard/SKILL.md): generate a terminal wizard for manual setup steps, with a bundled Bash template.
- [`grill-me`](skills/grill-me/SKILL.md): stress-test a plan with dependency-ordered questions and recommendations.
- [`handoff`](skills/handoff/SKILL.md): write a concise continuation document for a fresh agent.

Invoke a skill by name using your agent's skill interface, or ask for its task in natural language. The ten skills above use portable frontmatter and relative resource links, with no required provider-specific tool names. Agents can read linked `SKILL.md` files directly when no skill invocation tool exists. Delegation is optional and follows the host's capabilities and user instructions; direct execution remains available. Tracker integrations and HTML preview are used when available, with local files as the fallback. The wizard template requires Bash and uses `gh` only for requested GitHub configuration.

These skills are adapted from [Matt Pocock's skills](https://github.com/mattpocock/skills). See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for pinned source paths, licensing, and adaptation details. Host discovery paths are covered by the installer below; live behavior in each agent still depends on that host's tools and permissions.

## Install

```bash
git clone https://github.com/JamalLyons/agent-workforce-skills ~/Developer/GitHub/agent-workforce-skills
~/Developer/GitHub/agent-workforce-skills/install.sh
```

Clone it anywhere; the location above is just an example. The agents see the skills through links, so edits in the clone take effect right away. If you move the clone, run `install.sh` again from the new location to repoint the links.

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
skills/<other-skill>/          SKILL.md and any bundled references or templates
licenses/                      third-party license texts
tests/                         shared packaging and installer checks
```

Each skill's scripts resolve paths relative to its own folder, and the skills refer to each other as siblings (`<skill-dir>/../<other-skill>`), never through an agent-specific path. `start-issue-workforce` uses `create-workforce-epic`'s `epic_status.py` for epic queues when it is installed and falls back to `gh api` otherwise.

## Validation

```bash
python3 -B -m unittest discover -s tests
for s in skills/*/; do
  [ -d "$s/tests" ] || continue
  (cd "$s" && python3 -B -m unittest discover -s tests) || exit 1
done
bash -n install.sh skills/start-issue-workforce/scripts/detect_checks.sh skills/wizard/template.sh
```
