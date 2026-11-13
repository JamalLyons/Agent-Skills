---
name: wizard
license: MIT
description: Generate an interactive bash wizard that walks a human through steps only they can perform. Use when provisioning infrastructure, setting up credentials or CI secrets, walking an unfamiliar third-party dashboard, or running a one-off migration or cutover. Don't invoke this for steps the agent can perform itself.
---

# Wizard

A **wizard** is a bash script that walks a human, step by step, through a manual procedure that's tedious to do by hand and tedious to re-explain to an AI every time. It opens each URL, says exactly what to click and copy, captures the values, writes them where they belong (`.env`, GitHub secrets), confirms at every stage, and shows how many stages are left. It might configure third-party services, run a one-off migration, or move the project from one state to another.

The delightful UX is already solved by [template.sh](template.sh): stage-by-stage progress, confirmation gates, cross-platform URL opening (including WSL), hidden secret entry, idempotent `.env` upserts, `gh secret`/`gh variable` writes, and a closing summary. **Your job is only to scope the procedure and author its stages.** The library above the `STAGES` marker is identical in every wizard; that consistency is the point: never hand-edit it.

A wizard is ephemeral by default: built for one run, saved to a scratch or `scripts/` path, deleted when the job's done. Keep it in the repo only when the user wants a repeatable setup path. Commit only if requested or already authorized.

## Process

### 1. Scope the procedure

Work out every manual step the human must take and every value that gets captured along the way. Read the repo first, don't ask cold:

- For setup: `.env`, `.env.example`, `.env.*`, `README`, `docker-compose*`, framework config, and `.github/workflows/*` (every `secrets.*` / `vars.*` reference is a value the wizard must produce).
- For a migration or transition: the current state, the target state, and the irreversible actions between them.

Use requirements already established, then show the ordered stages and where each value goes. Ask only for unresolved choices that affect the procedure. Generate the complete reviewable script before any final execution approval.

**Done when:** every stage is named in order, every destination has an explicit project root/env path and GitHub `owner/repo` when applicable, and for each captured value you know where it comes from, where it goes, whether it is secret, and whether it is required.

### 2. Map each stage's journey

For each stage, write the precise path a human follows: which URL to open, what to do there, where a value is shown, which variable it fills: e.g. "Dashboard → Developers → API keys → Reveal test key → copy". Where you don't actually know the current UI or the exact command, say so and ask the user or check the docs: never invent steps that may not exist.

**Done when:** every stage traces to concrete instructions a stranger could follow.

### 3. Author the wizard

Copy `template.sh` to the target path. Replace the example stage with one `stage` per step, in dependency order. Use the library helpers: `stage`, `say`/`step`, `open_url`, `ask`/`ask_secret`, `write_env`, `set_secret`/`set_var`, `pause`/`confirm`. Set `TOTAL_STAGES` to the number of stages you wrote.

Before the first prompt or browser action, call `configure_destinations` with the resolved absolute project root, an explicit env path (absolute or relative to that root), and the target GitHub `owner/repo` when needed. Pin these values in the generated script from the agreed setup scope, or require explicit runtime arguments for a relocatable script. Never infer destinations from the launch directory. The untouched template requires `/absolute/project/root owner/repo` arguments and exits before doing anything when they are absent. `write_env` rejects an unpinned relative path; GitHub writes require and pass an explicit `--repo`.

`ask` and `ask_secret` require nonempty input by default. Enter preserves an existing nonempty value; EOF fails without assignment, including a partial line. Use the third argument `optional` only for deliberately empty values. A fourth argument can name a defined validator function that accepts the value and returns success/failure; its output is suppressed. Required blank/invalid values stop the stage rather than writing incomplete credentials. If a setup supports clearing a stored value, make that a separate explicit action; Enter is never removal.

Identify the consumer of each `.env` file before writing it. The template supports a conservative **non-expanding dotenv** subset: single-line values in single quotes, or apostrophe-containing values in double quotes when they contain no double quotes or backslashes. It preserves literal spaces, `$`, `#`, Unicode, and backslashes inside single quotes. It rejects multiline values and ambiguous quote/backslash combinations before changing the file. For those values, or consumers that interpolate variables or interpret different escapes, use and round-trip test the project's native serializer instead. Do not source the generated `.env` as shell code or translate dotenv values with shell escaping. Unsupported existing values are not offered as decoded defaults.

Hold the bar the template sets: open the URL before asking for its value, use `ask_secret` for anything secret, `write_env` every persisted value, `set_secret` only the values CI actually needs, and `confirm` before any irreversible action. Each `stage` clears the screen so only the current step is visible: keep a stage to one focused task so nothing the human needs scrolls away. Don't touch the library above the marker.

### 4. Verify and hand off

- `bash -n <script>`; run `shellcheck` if available.
- Test helpers from a different launch directory with temporary paths and a stubbed `gh`: confirm only the pinned env file changes, every GitHub write names the intended repo, and blank/EOF/invalid inputs leave saved values intact. Never use live credentials for these tests.
- Round-trip representative dummy values through the actual `.env` consumer; syntax checks alone cannot establish value preservation. The template can be sourced in isolated helper tests without running its example stages.
- `chmod +x <script>`.
- Don't run it end-to-end yourself: it opens browsers and blocks on human input. Trace it statically instead: every value from step 1 is captured and lands where step 1 said, and every `set_secret` name exactly matches a `secrets.*` reference in CI.
- Tell the user how to run it. If it's a requested repeatable setup path, link it from the README. Commit only when authorized. The generated script is for the human to run in their terminal; never ask them to paste secrets into chat. Use the host's secure secret-input mechanism if a value must be supplied to the agent.
