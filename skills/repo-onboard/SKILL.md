---
name: repo-onboard
description: Create or refresh a repository's agent instruction file (AGENTS.md, CLAUDE.md, or the host's equivalent) from commands and paths verified in the repo, so later agent sessions start with correct install, build, test, lint, and layout facts. Use when the user asks to onboard a repo for agents, write or update AGENTS.md/CLAUDE.md, init agent instructions, or when agents keep getting build/test commands wrong. Refreshes existing files in place and preserves human-written notes. Do not use for domain glossary/ADRs (domain-modeling) or architecture review (improve-codebase-architecture).
---

# Repo onboard

Write the short file a new agent needs before its first command: exact commands, a map, and repo-specific rules. Every line is either observed in the repo or marked unverified. Use the host's tools; no particular agent or provider is assumed.

## 1. Find what already exists

Before writing, look for every instruction surface: `AGENTS.md`, `CLAUDE.md` (follow its `@path` imports), `.cursor/rules/` and `.cursorrules`, `GEMINI.md`, `.github/copilot-instructions.md`, `CONTRIBUTING.md`, and nested copies in subpackages.

- One exists: **refresh mode**. Edit it in place. Do not create a second file alongside it.
- Several exist: keep each file's human-written rules. Fix facts where they live; do not copy the same content into every file.
- User wants both AGENTS.md and CLAUDE.md: make one canonical (default `AGENTS.md`). The other only imports or points to it (`@AGENTS.md`, plus any tool-specific lines).
- None exists: create the one file the user or host asks for. If they don't say, default to `AGENTS.md`.

Content written by people (team notes, warnings, ownership, "ask X before Y") is kept word for word unless it is factually stale. Then fix it and report the change. Never delete it without saying so.

## 2. Discover by reading and running

Sources, from most to least trusted: CI workflows, then manifests and lockfiles (`package.json` + `packageManager`, lockfile type, `pyproject.toml`, `Cargo.toml`, `go.mod`, ...), then task runners (`Makefile`, `justfile`, `Taskfile`, turbo/nx config), then docs. When README or CONTRIBUTING disagrees with CI or the manifest, trust CI/manifest and list the drift in your report. Do not edit those docs unless asked.

Collect:

- **Commands**: package manager and exact install, build, test, lint, typecheck, and format commands. Include how to run a single test file or test name, and per-package commands in a monorepo.
- **Environment**: runtime versions, required env vars (from `.env.example` or the CI `env:`), services (DB, queues, containers), codegen steps.
- **Map**: top-level directories and their purpose, entrypoints, workspace packages.
- **Rules**: conventions the code or config actually enforces (lint config, tsconfig strictness, CI diff checks, existing rule files). Generated or vendored paths agents must not edit, and how to regenerate them. Branch and PR conventions from CI triggers, templates, or CONTRIBUTING.
- **Gotchas**: things CI does that a local run would miss (frozen lockfile, codegen diff check, `TZ`, ordering).

**Verify** each command where it is safe. Read the script or target first. Run only local, read-only or build/test commands. Never run deploy, publish, release, migration, or other network-mutating commands. Prefer offline installs and don't install anything globally. Mark any command you didn't run `(unverified)` and give the reason in a few words. A missing tool means unverified, not broken.

## 3. Write it short

Follow [references/template.md](references/template.md). Commands first, then the map, then rules. Aim for under 150 lines. Cite file paths so readers can check the source.

Leave out generic advice the model already knows (write tests, keep functions small), anything you invented without evidence, secrets, and long prose. If a section has nothing verified, drop it instead of padding it.

In refresh mode, compare each existing command and path with what you observed. Fix stale ones, remove dead paths, add missing essentials, and keep the file's existing structure and voice where it works.

## 4. Scope and report

Write only the instruction file(s). Don't change code, config, README, or CI. Commit, push, or open a PR only when asked.

Report:

- the files created or edited
- each command and whether you verified it
- what changed in refresh mode: stale items fixed, content preserved, anything removed
- drift found in other docs, left for the user to decide
- open questions you couldn't settle from the repo
