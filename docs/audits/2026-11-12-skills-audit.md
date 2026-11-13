# Skills audit — 2026-11-12

## Assessment

Keep all 12 skills. The collection is strongest at turning conversations into planned work and carrying GitHub issues through verified implementation. The biggest gains are better behavioral verification, more reliable handoffs between skills, and a few concrete helper fixes. Adding many more planning skills would increase overlap before addressing these gaps.

This is an assessment of likely workflow value and the current implementation, not measured personal usage or a demonstrated productivity gain. Three GPT subagents reviewed separate groups; the lead reviewed cross-skill contracts, packaging, tests, and reproduced selected defects. No non-GPT agents were used.

Audited snapshot: `trunk`, `6144c139af4158d37a9cbfd3f1f42aeba13f1d1a`. Working tree was clean at intake. All 12 entry files, their supporting references/templates, installer, Python helpers, tests, and evaluation catalogs were examined across the team. Skill implementations were not changed; this report is a new audit artifact.

## What works well

- **A coherent workflow:** research → challenge decisions → specification → epic → implementation → review → handoff. Domain modeling and codebase design support the chain without requiring an extra implementation framework.
- **Good restraint:** research separates inference from verification; to-spec avoids another interview; workforce honors existing approval, bounds retries, preserves dirty work, and verifies actual artifacts rather than accepting child reports.
- **Practical orchestration:** dependency ordering, human-only tasks, ownership, stale-result handling, PR identity, and deferred findings receive unusually specific treatment.
- **Mostly compact instructions:** entry files range from 15 to 115 lines. Keep the short skills short; length alone is not a quality problem.
- **Useful offline tests:** all 73 existing tests passed. Epic application tests cover simulated partial failures and idempotency, not just formatting.

## Fix first: reproducible helper defects

### F01 — Issue discovery silently truncates, weakening duplicate prevention

**Priority: high; conditional on a large labeled backlog.** [epiclib.py:466](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/create-workforce-epic/scripts/epiclib.py:466) stops pagination at 1,000 results even when the final page is full. It returns an ordinary list with no indication that discovery is incomplete. [apply_plan.py:59](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/create-workforce-epic/scripts/apply_plan.py:59) uses that list to find existing epic/task markers.

An older marked epic or an unlinked task beyond that bound can be missed, allowing a rerun to create a duplicate. Already linked tasks have the separate sub-issue lookup as another defense. An offline fake returning a full page forever reproduced a normal return of 1,000 results after ten calls.

**Change:** paginate to exhaustion, or fail explicitly at a configured bound and prohibit writes based on incomplete discovery. Add an older-marker-beyond-1,000 regression case, including a lost-create-response recovery.

### F02 — Wildcard ownership checks miss real overlapping files

**Priority: high for parallel planning.** [epiclib.py:69](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/create-workforce-epic/scripts/epiclib.py:69) removes wildcard suffixes, then compares only directory containment. Reproduced: `paths_overlap("src/foo*.ts", "src/foobar.ts")` returns `False`, although both declarations own the same file. The validator therefore misses its overlap warning. Lead verification remains a second defense; this helper defect alone does not launch simultaneous writers.

**Change:** match literals against globs and conservatively flag potentially intersecting patterns, including future files. Add partial-filename glob, directory glob, root-path, and glob-versus-glob cases. Clearly document whether owned paths are patterns or literal prefixes.

### F03 — Wizard writes shell quoting into dotenv files

**Priority: high for configuration correctness.** [template.sh:138](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/wizard/template.sh:138) writes apostrophes using shell escaping. For the value `it's-a-token`, it produces `TOKEN='it'\''s-a-token'`. Node's native `util.parseEnv` reads that as `TOKEN="it"`. The delivery reviewer reproduced this with the real helper in a temporary file; the lead independently confirmed the parser result.

**Change:** identify the project's actual dotenv consumer, serialize for that format, and test a round trip through that consumer. Cover apostrophes, double quotes, spaces, backslashes, `$`, `#`, Unicode, and supported multiline values. Do not promise one universal shell/dotenv format. Syntax and ShellCheck success cannot establish serialization correctness.

### F04 — Duplicate-marker recovery instructions do not resolve the error

**Priority: medium; code-path verified.** [apply_plan.py:87](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/create-workforce-epic/scripts/apply_plan.py:87) and [apply_plan.py:125](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/create-workforce-epic/scripts/apply_plan.py:125) tell users to close duplicate issues. Discovery searches `state=all`, so closed duplicates retain their markers and still match on the next run.

**Change:** define canonical and superseded marker handling, or give accurate instructions for resolving marker identity. Do not silently pick a duplicate. Test the documented recovery procedure.

## Highest-value workflow improvements

### F05 — Give code-review an explicit correctness and regression pass

The current two axes—standards and spec—are valuable, but [code-review/SKILL.md:7](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/code-review/SKILL.md:7) does not independently require tracing runtime failure paths. A standards-compliant implementation can match a written spec and still mishandle concurrency, resource cleanup, authorization, errors, or data integrity.

Keep the two labels, and add a correctness pass that works even without a spec. Make the user's explicit spec authoritative before inferred commit references; the current source order at [line 26](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/code-review/SKILL.md:26) does the reverse. Require a triggering scenario, consequence, file/line, evidence, and severity. Deduplicate and order actionable findings by severity while retaining axis labels. The fixed 400-word briefs and prohibition on aggregation at [line 77](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/code-review/SKILL.md:77) can bury or truncate important findings on large changes. State unreviewed coverage explicitly. This need not mean three delegates for every review; passes can share one reviewer.

### F06 — Connect specifications to delivery through acceptance IDs

[to-spec/SKILL.md:21](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/to-spec/SKILL.md:21) provides stories and testing decisions but no explicit acceptance-criteria section. Epic planning then extracts or derives `C1..Cn` at [create-workforce-epic/SKILL.md:39](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/create-workforce-epic/SKILL.md:39).

Add stable acceptance IDs and observable success/failure cases to to-spec, preserving agreed decisions versus proposals and unresolved blockers. Carry the IDs through task issues, implementation evidence, and review. This prevents repeated interpretation and makes completion easier to judge. Add rollout, compatibility, or data-migration criteria only when relevant to agreed scope.

### F07 — Turn workforce recovery requirements into validated state

[start-issue-workforce/SKILL.md:103](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/start-issue-workforce/SKILL.md:103) requires owner detection, atomic updates, active children, attempts, approvals, accepted SHAs, and retained follow-ups. The supplied helpers do not validate this ledger or its transitions.

Add a small versioned state helper with validated transitions, artifact identity, integrated-step deduplication, atomic persistence, and explicit ownership semantics. A `resume/status` command should expose the next actionable step, active work, blocked criteria, and unanswered follow-ups. Render Markdown from this state rather than maintaining two independent truths. Start with validation and reporting; avoid building a second full orchestration platform.

### F08 — Make evaluations executable and measure whether skills help

Ten skills have no checked-in behavioral evaluation scenarios. The two workforce skills have useful catalogs, prompts, and graders, but their documentation explicitly distinguishes specifications from executed agent runs. This audit did not execute those agent scenarios. The 73 passing tests prove helper/package behavior, not adherence to orchestration prose or superiority over an ordinary GPT session.

Start with 2–3 pinned scenarios per skill: ordinary use, a boundary case, and a case where it should decline or avoid extra work. Run fresh-context GPT sessions with and without the skill. Grade actual outputs/tool traces, record host/model/fixture revision, and compare correctness, unnecessary questions, tool calls, elapsed time, and tokens where available. Use mocked external mutations. Add a one-command local check runner and CI for the three existing suites; no CI workflow is checked in.

First orchestration cases: existing authorization, GPT-only routing, timeout with a live writer, pre-staged user changes, injected issue instructions, resume after integration, and unanswered follow-up retention. These test promises that helper unit tests cannot prove. The official [Agent Skills evaluation guide](https://agentskills.io/skill-creation/evaluating-skills) recommends baseline comparisons and clean evaluation contexts.

### F09 — Pin wizard destinations and validate required input

[template.sh:27](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/wizard/template.sh:27) defaults to the launch directory's `.env`; [line 159](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/wizard/template.sh:159) and [line 173](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/wizard/template.sh:173) infer the GitHub repository from the current directory. Generated scripts may live in scratch locations. Starting one from another checkout can therefore configure the wrong destination.

Generate and validate an explicit project root, env path, and `owner/repo`; pass `--repo` to GitHub writes. Add required/optional inputs and validators. The real `ask_secret` helper currently accepts an empty Enter with no saved value; the reviewer reproduced success with an empty result. Test helper behavior with temporary directories and stubbed `gh`/browser commands, including interruption, EOF, reruns, file modes, and wrong-directory launches.

### F10 — Detect scope drift when reusing existing task issues

[apply_plan.py:129](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/create-workforce-epic/scripts/apply_plan.py:129) warns about changed titles but does not compare existing acceptance/verification sections against an updated plan. The skill intentionally never edits existing task bodies. A same-title replan can therefore report reuse while implementation still consumes old issue requirements.

Compare normalized managed sections with the rendered plan and report exact drift. Require a reconciliation disposition before presenting the updated plan as applied. Preserve the existing separation between planning and authorized issue editing.

## Improve the smaller skills without adding ceremony

### F11 — Bound the grill-me question frontier

[grill-me/SKILL.md:9](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/grill-me/SKILL.md:9) asks every currently answerable question in one round. Keep dependency ordering and its excellent distinction between facts the agent can investigate and decisions the user owns. Limit ordinary rounds to about three consequential questions; allow short/thorough modes and accepting the recommended answers together. Persist settled and deferred decisions so an interview ends in a reusable result.

### F12 — Soften architecture rules and require migration evidence

[improve-codebase-architecture/SKILL.md:13](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/improve-codebase-architecture/SKILL.md:13) forbids “service,” “API,” and related terms, conflicting with [codebase-design/SKILL.md:13](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/codebase-design/SKILL.md:13), which preserves established terminology. Preserve repository language and use shared vocabulary to explain tradeoffs.

Treat “one adapter means a hypothetical seam” and “fewer methods = fewer tests” as heuristics with counterexamples. Existing seams can protect ownership, invariants, or security even with one adapter; interface size does not determine behavioral complexity. Architecture candidate reports should show a concrete costly change or failure, expected benefit, confidence, effort, migration risk, and an incremental path. Allow “leave it alone.” Keep a durable decision summary when requested, since the HTML currently lives in temporary storage.

### F13 — Make TDD rules follow the behavioral contract

[tdd/SKILL.md:29](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/tdd/SKILL.md:29) discourages direct database checks and its references broadly discourage collaborator assertions. Usually helpful, these rules need exceptions when persistence, ordering, idempotency, or external side effects are the behavior under test. Owning an adapter does not make it an inappropriate test double.

Retain vertical slices, independent expected values, and checking the actual red failure. Add a lightweight finish step: relevant existing regressions, behavior covered, failure paths checked, and what remains unverified. Avoid an unconditional full-suite requirement for every slice.

### F14 — Tighten research, domain-modeling, and handoff outputs

- **Research:** add the precise question/scope, conclusion, source version/date when relevant, and a sufficient-evidence stopping rule. Preserve its small size and strong uncertainty handling. [research/SKILL.md:9](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/research/SKILL.md:9)
- **Domain modeling:** discover existing glossary/ADR locations and formats before creating root files. Mark proposals versus accepted definitions; avoid silently revising accepted terminology. [domain-modeling/SKILL.md:41](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/domain-modeling/SKILL.md:41)
- **Handoff:** add a unique filename, exact next command, active delegate/background work, worktree identity, and stale-state checks before mutation. Its existing constraints, authorization, validation limitations, and artifact references are already strong. [handoff/SKILL.md:17](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/handoff/SKILL.md:17)

## Packaging and portability

The installer is simple, repeatable, preserves real-directory collisions, and has useful isolated tests. Two improvements matter:

1. [install.sh:50](/Users/jamallyons/Developer/GitHub/Agent-Skills/install.sh:50) replaces any differently targeted same-name symlink, including a valid link owned by another skill collection. Default to reporting a collision for foreign links; provide explicit replacement and dry-run options. This is an observed code path, not a claim that any user's links were overwritten during this audit.
2. [tests/test_packaging.py:13](/Users/jamallyons/Developer/GitHub/Agent-Skills/tests/test_packaging.py:13) uses regexes rather than validating actual YAML or the full metadata constraints. Add frontmatter parsing, name/description bounds, and manifest checks. Include sibling skill dependencies and required runtimes in compatibility guidance. The [Agent Skills specification](https://agentskills.io/specification) defines the metadata constraints and supports optional environment compatibility. Ten skills have `agents/openai.yaml`; the two workforce skills do not. Matching UI metadata would be useful polish, not a format-compliance requirement.

Keep host-specific dispatch separate from workflow policy. The workforce routing reference still gives standalone Sonnet/Opus defaults while config defines a different multi-provider roster. Explicit GPT-only restrictions take precedence today, but named local profiles and a single source for defaults would reduce repeated configuration. The wording that `--set` “persists” percentages also needs clarification: the script applies overrides to that invocation; it does not save them.

## Per-skill usefulness and recommended disposition

These are qualitative judgments based on the instructions and workflow role, not usage analytics or numerical benchmark scores.

- **start-issue-workforce — Core delivery skill; high value.** Keep its recovery, verification, and deferred-item rules. Prioritize validated state, executable evals, reusable profiles, and a documented small-task minimum path. It already permits direct handling and lighter review for tiny changes; make that route easy to follow.
- **create-workforce-epic — Core planning skill; high value.** Strong decomposition, human tasks, and offline apply checks. Fix discovery/overlap defects and scope-drift reporting first.
- **to-spec — Core bridge; very high potential.** Add acceptance IDs and observable criteria. Its existing no-interview and no-invented-requirements rules should stay.
- **code-review — Core quality gate; high potential.** Add correctness coverage and a useful severity-ordered output. Keep standards/spec traceability without letting smell suggestions dominate bugs.
- **tdd — High value when test-first work is requested.** Preserve the concise red/green loop; add contract-based exceptions and completion evidence.
- **handoff — High value per instruction token.** Small reproducibility improvements suffice. Do not expand it into another project-management system.
- **research — High value, broadly portable.** Strong primary-source and uncertainty discipline. Add a compact output/stopping contract.
- **grill-me — High value before consequential design work.** Bound question rounds and capture decisions. Avoid triggering a full interview for routine implementation choices.
- **codebase-design — Useful shared reference.** Keep the vocabulary and alternative-design pattern; add counterexamples to universal rules. It should inform design without prescribing every repository's language.
- **improve-codebase-architecture — Valuable for active, costly change areas.** Good hotspot focus and no-candidate exit. Require evidence, effort/risk, and an incremental migration path before a strong recommendation.
- **domain-modeling — Situationally high value.** Most useful in systems with overloaded terminology or multiple contexts. Follow existing documentation conventions and avoid creating documents for trivial naming decisions.
- **wizard — Useful specialized tool.** Strong human-only setup boundary, hidden input, and reviewable scripts. Repair serialization/destination/input behavior before extending its features.

## What to add for a better workflow

Prefer three targeted additions and two shared capabilities over more overlapping orchestration skills:

1. **Bug investigation:** symptom → minimal reproduction → competing hypotheses → evidence → root cause → regression test → bounded fix. Include baseline/environment checks and a stopping rule. Existing design and TDD skills do not fully supply this diagnosis workflow.
2. **Skill evaluation and maintenance:** run pinned GPT scenarios, compare with a baseline, inspect tool traces, and produce a concise regression report. Build this on the existing eval catalogs rather than replacing them. It should test negative triggers and composition as well as happy paths.
3. **PR follow-through:** respond to reviews, diagnose CI, update the branch, and verify the latest head with bounded retries. Keep merge/deploy authority explicit. Reuse an existing autopilot skill where available rather than duplicating it in this collection; add a documented handoff from workforce.
4. **A local workflow profile, not another skill:** provider allowlist, model preferences, concurrency, publication scope, check/review budget, and preferred documentation locations. Keep personal settings outside shared roster defaults; user instructions always override profiles. A GPT-only profile would make requests like this one easier to repeat.
5. **A shared acceptance/evidence contract:** requirement ID → implementation/task → observed verification → remaining limitation. Reuse it in specs, epics, workforce, review, and handoff rather than copying policy into each entry file.

A later addition could reconcile approved follow-ups into existing issue scope without losing markers. First extract and test the workforce's existing follow-up behavior; do not create another tracker-maintenance workflow before that is reliable.

## Suggested implementation order

1. Repair pagination, overlap detection, wizard dotenv serialization, and duplicate-marker remediation; add meaningful regression tests.
2. Improve code-review correctness coverage and to-spec acceptance criteria; test their composition with epic planning.
3. Add a single check command/CI and execute a small pinned GPT evaluation suite. Establish a baseline before rewriting more skill prose.
4. Add workforce state validation/status and local profiles, then validate interrupted/resumed runs.
5. Tune question load, architecture guidance, and smaller output contracts. Add bug investigation and PR follow-through only after checking for reuse of existing skills.

## Verification and limits

Executed successfully:

```sh
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s skills/start-issue-workforce/tests -v
python3 -m unittest discover -s skills/create-workforce-epic/tests -v
```

Results: packaging **3/3**, workforce helpers **22/22**, epic helpers **48/48**. The delivery reviewer also ran `bash -n` and ShellCheck on the wizard template; both passed. Selected offline reproductions exposed gaps outside those checks.

Not established: end-to-end agent adherence, real GitHub API compatibility, live cancellation semantics, actual model quota/cost, personal frequency of use, or productivity improvement versus no skill. No live GitHub writes, publishing, credential changes, or full interactive wizard run occurred. The first-party Agent Skills specification and evaluation guide were checked for the external format/evaluation recommendations above.
