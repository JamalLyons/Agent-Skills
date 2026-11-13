# Routing and recovery

`config.json` is an illustrative roster and advisory estimate configuration, not a required provider set. Use any model/provider supported and authorized by the current host, or perform scoped steps directly when delegation is unavailable. Optional [local profiles](profiles.md) keep personal routing preferences separate from shared defaults. Explicit user choices take precedence over the roster. A prohibition excludes a provider; "spare" makes it last resort. Routing cannot authorize cross-provider disclosure.

## Difficulty and usage

Easy: well-specified local pattern-following work, docs, fixtures, mechanical migrations. Hard: foundation interfaces, security, concurrency, native APIs, migrations, uncertain debugging, or subtle failures other steps depend on. If unsure choose hard.

Use `python3 <skill-dir>/scripts/route.py --steps hard,easy --json` for advisory suggestions. Supply per-invocation percentages with `--set gemini=30 --set gpt=70`; these mean weekly percent LEFT and are not saved. Use `--config /absolute/roster.json` for a different roster or `--profile /absolute/profile.json` for saved preferences. `--read-local-usage` explicitly opts in to recognized local cache reads; without it usage is unknown unless supplied. A weekly override changes only the weekly observation, retaining known session limits. `--avoid claude` is soft; `--exclude claude` is absolute. Pass capability-validated `--allow-model provider/model` entries to restrict suggestions to eligible targets. Apply explicit model/settings overrides in the plan and dispatch; do not permit fallback to violate them.

Reads of local usage are opt-in operational data for this workflow. Do not print or send the source files to children. Sources are caches, not live APIs. Old/expired/malformed observations become unknown, never a fabricated fresh 100%. Unknown usage uses the configured assumption and remains labelled unknown. Step costs are estimates; each invocation refreshes observations but does not measure consumption attributable to this run. Account for active work and explicit reserves in the ledger, not just independently repeated script outputs. Check session and weekly floors after each estimated allocation. Do not downgrade hard work to an easy model when the hard roster is exhausted; mark it blocked.

## Dispatch

Validate roster IDs and option values against capabilities. A short capability list is not exhaustive; search omitted models. Dispatch syntax depends on the host: do not assume another agent's tool names, model IDs, option fields, or checkout semantics exist. Use supported native delegation for matching capabilities. Without delegation, execute the planned steps directly and sequentially, preserving verification and recording the reduced independence of review. Without isolation, do not parallelize writers.

### Conditional T3 adapter

Only when running in T3 Code, follow its host-specific orchestration instructions: inspect `orchestrator_capabilities` once before the first delegate, validate exact provider/model/options (search omitted models), and prefer native dispatch only where the host permits it. Otherwise `delegate_task` takes `target.providerInstanceId`, `target.model`, `target.options`, a complete `task`, and the appropriate role.

- Sequential: `isolation: "shared"`, `mode: "wait"` if the current turn needs the result, with a finite wait deadline. A wait timeout leaves the child running.
- Parallel: `isolation: "worktree"`, `mode: "async"`, separate owned files and resources; no checkout commands in the prompt. Verify parent/base identity.
- Do not override runtime permission mode unless the user explicitly requests it and the host permits it. A narrow mode does not ensure read-only behavior; provide scope instructions and inspect resulting Git state.
- Follow `next` and end the turn when told. Do not poll, sleep, or launch a replacement. If a question/approval blocks a child, answer only facts and permissions already authorized; otherwise surface the pending request. Never self-approve a child action outside scope.

### Other hosts

Use their actual available tools, models and options; no provider or model family is preferred by this workflow. If an explicitly requested provider/model/setting is unavailable, report the limitation instead of silently substituting. A single-agent host can still use the workflow through direct sequential work and clearly disclosed self-review.

## Recovery and retry classification

1. **Wait timeout, interruption, lost result, uncertain tool response:** task may still be running. Retain its ID and follow host continuation. To abandon, use the host's supported cancellation mechanism (`task_cancel` in T3) and establish terminal status before reuse. If cancellation cannot be confirmed, quarantine that checkout; do not create another writer or integrate late output.
2. **Known terminal provider/rate-limit error before usable work:** record partial files and the failure. Exclude that provider temporarily for this run as appropriate; retry on an eligible candidate within the step budget only if user model/provider constraints allow. One failure does not prove all models/providers unavailable. Re-check capabilities after an availability error.
3. **Invalid request/options:** correct the request using the real schema; do not classify this as depleted quota or fan out retries.
4. **Verification failure or low-confidence result:** inspect code/evidence and give concrete bounded rework; do not treat the model's confidence as a pass or fail. Keep accepted work, identify partial changes, and do not inherit an unknown dirty state into the next attempt.
5. **Refusal, privacy restriction, denied permission:** stop that action. Do not evade by provider switching. Continue independent authorized work if possible.

Default attempt budget is defined once in SKILL.md, including escalation and re-scoping; no nested retry budgets. Every dispatch (including a failed launch) counts toward its original step's budget. Small lead fixes do not justify another delegate. A new T3 review/re-check is a fresh delegate with original scope and current findings; do not use thread messaging for it. Native continuation is permitted only through the host's supported API after the earlier writer has stopped.

Track each active attempt and estimated allocation centrally. Shared provider quota (e.g. Composer and Grok on Cursor) is counted once; estimated allocation reservations are not observed usage. Concurrency is limited by runtime capacity, approved provider use, file ownership, and external resources, not provider count alone.
