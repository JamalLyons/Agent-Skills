# Local workflow profiles

Profiles are optional, explicitly selected defaults for any skill-capable agent. Store personal files outside the shared skill checkout, for example under the operating system's user configuration directory. They contain preferences, not secrets. Do not auto-load a repository-provided file as permission to disclose code or publish work.

The advisory router accepts `--profile /absolute/profile.json`; its optional `config` points to a roster JSON, relative to the profile file or absolute. `--config` explicitly replaces that roster. A roster uses the same `tiers`, `usage_overrides`, and `routing` shape as bundled `config.json`, with any host-supported provider/model IDs and exact native option names. Empty tiers are allowed and block that tier rather than downgrade work. The bundled model roster is an example, not a dependency.

```json
{
  "version": 1,
  "config": "my-roster.json",
  "allow_models": ["local-engine/small", "other-engine/deep"],
  "exclude": [],
  "avoid": ["other-engine"],
  "workflow_preferences": {
    "max_concurrency": 2,
    "review_budget": 1,
    "publication": "local-only"
  }
}
```

All fields except `version` are optional. `allow_models` is a provider/model allowlist; an explicitly empty list blocks all models. `exclude` is a prohibition; `avoid` is a soft preference. The CLI's repeated `--allow-model`, `--exclude`, or `--avoid` arguments replace the corresponding saved list for that invocation. `--ignore-profile-routing` ignores all three saved lists. Use those overrides only to implement the user's current instructions, not to work around a restriction. Exact configured provider IDs take precedence over convenience aliases such as `gpt` or `claude`.

`max_concurrency` is a positive integer and `review_budget` is a nonnegative reviewer-count preference; neither overrides host capacity, task risk, or an explicit user limit. `publication` is `local-only` or `propose-pr`: the latter requests preparation of a proposed PR, not permission to push, create, merge, or deploy. The router returns these workflow preferences for the lead to apply; it does not enforce concurrency or perform publication. A profile grants no permission, proves no model exists, and cannot supersede current user/repository/host instructions.

```sh
python3 <skill-dir>/scripts/route.py --profile /absolute/profile.json --steps easy,hard --json
python3 <skill-dir>/scripts/route.py --config /absolute/my-roster.json --steps hard --allow-model other-engine/deep --set other-engine=70 --json
```

The router reads files and prints advice; it never saves overrides, invokes models, or sends network requests. `--set` means weekly percent **left** for this invocation. Recognized local account/cache reads require `--read-local-usage`; otherwise unknown usage remains labeled as an assumption. Other providers can use supplied quota overrides, or leave usage unknown. Revalidate model IDs/options against actual capabilities and carry current user constraints into every invocation and retry.

If Python, a usable roster, or delegation is unavailable, the skill still works: select a permitted capable agent through the host's available mechanism, or execute direct sequential steps, record limitations, and keep acceptance/verification discipline. Do not invent routing observations, delegation APIs, or independent review that did not occur.
