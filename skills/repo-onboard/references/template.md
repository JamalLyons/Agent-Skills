# Instruction file template

Fill this in with facts you observed. Delete any section that has nothing verified. Keep the whole file under 150 lines. Angle-bracket text is placeholder.

```markdown
# <Project name>

<One sentence: what this repo is and what it ships.>

## Commands

Package manager: <pnpm 9 (packageManager in package.json)>. Runtime: <Node 20 (engines, CI)>.

| Task | Command | Source |
| --- | --- | --- |
| Install | `<pnpm install --frozen-lockfile>` | <.github/workflows/ci.yml> |
| Build | `<pnpm build>` | <package.json> |
| Test (all) | `<pnpm test>` | <package.json> |
| Test (one) | `<pnpm vitest run test/parse.test.ts -t "name">` | <vitest> |
| Lint | `<pnpm lint>` | <package.json> |
| Typecheck | `<pnpm typecheck>` | <package.json> |
| Format | `<pnpm format>` | <package.json> |

Commands marked `(unverified: <reason>)` were not run.

CI runs, in order: <install, lint, typecheck, test> (<.github/workflows/ci.yml>). Run the same before you push.

## Environment

- <Copy `apps/web/.env.example` to `.env.local`; requires NEXT_PUBLIC_API_URL.>
- <Postgres 16 via `docker compose up db` (compose.yaml).>
- <CI sets TZ=UTC; date tests assume it.>

## Layout

- `<src/>`: <library source; entry `src/index.ts`>
- `<test/>`: <vitest tests, `*.test.ts`>
- `<apps/web/>`: <Next.js app (`@acme/web`)>
- `<packages/api-client/src/generated/>`: <generated, do not edit>

## Rules

- <Do not edit `<path>`; regenerate with `<command>`. CI fails on diff.>
- <Named exports only in packages/ui (.cursor/rules/style.mdc).>
- <PRs target `main`; CI runs on pull_request only.>

## Notes from maintainers

<Human-written content from the existing file, kept word for word except for factual fixes.>
```

## Paired files

If both `AGENTS.md` and `CLAUDE.md` are wanted, the non-canonical one is just a pointer:

```markdown
@AGENTS.md
```

Put tool-specific additions below the import only when they apply to that tool alone.
