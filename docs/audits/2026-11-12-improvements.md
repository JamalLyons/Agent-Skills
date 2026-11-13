# Skills audit implementation — 2026-11-12

Implemented the audit improvements with one scoped GPT-agent assignment per numbered finding, separate assignments for packaging and universal profiles, and new-skill assignments. The lead integrated shared contracts and independently checked the combined work. Changes remain uncommitted; no PR, publishing, live forge changes, or global skill installation occurred.

The resulting 14 skills use the portable Agent Skills entrypoint. They do not require GPT, ChatGPT, a particular model/provider, or a proprietary orchestration runtime. Optional host UI metadata and conditional host examples remain optional. Operations still require their documented tools/access; unsupported delegation falls back to direct sequential work. Saved profiles never grant permission.

## Findings addressed

- **F01:** complete issue pagination, explicit failure for exceeded caller bounds, and large-backlog/lost-response regression coverage.
- **F02:** conservative literal/glob ownership overlap, including future files and repository roots.
- **F03:** dotenv serialization roundtrips for the supported format; unsupported values fail before mutation, with project-native serialization guidance.
- **F04:** accurate canonical/superseded marker recovery; closing duplicate issues alone is no longer suggested as a fix.
- **F05:** correctness review alongside standards/spec, explicit-spec precedence, verified/deduplicated severity-ordered findings, and coverage limits.
- **F06:** stable acceptance IDs and a shared requirement → task/change → actual evidence → limitation contract across spec, epic, workforce, and review.
- **F07:** versioned local run state, validated transitions, writer ownership, atomic persistence, artifact/integration identity, and retained follow-ups. Status/resume reads observations rather than controlling live agents.
- **F08:** portable evaluation manifests/fixtures for every skill, an argv-based adapter harness, one check command, and CI. Process completion and semantic grades are kept separate.
- **F09:** pinned wizard destinations and GitHub repository, required/optional validated input, EOF handling, cleanup, and incomplete-setup reporting.
- **F10:** existing issue-scope drift is reported before writes. Custom generated headings are compared, including the integration review's reproduced summary-heading defect; human content is preserved.
- **F11:** bounded consequential interview rounds, short/thorough pacing, grouped acceptance, and concise decision summaries.
- **F12:** repository vocabulary preserved, contextual architecture heuristics, concrete friction evidence, migration risk/effort, and a valid leave-alone outcome.
- **F13:** test advice follows behavioral contracts, including persistence/ordering/side effects; completion evidence and limitations remain lightweight.
- **F14:** scoped research/stopping rules, existing glossary/ADR conventions, proposed versus accepted definitions, and reproducible handoffs.
- **Packaging:** foreign-link collision protection, explicit replacement, mutation-free install preview, real YAML metadata validation, and development-only parser dependency.
- **Profiles/universality:** arbitrary host-supported rosters, explicitly selected local profiles, invocation-only overrides, opt-in usage-cache reads, and capability-based direct/delegated execution.

## New skills

- [Bug investigation](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/bug-investigation/SKILL.md): reproduction, discriminating hypotheses, evidenced cause, bounded correction when authorized, and verification limits.
- [PR follow-through](/Users/jamallyons/Developer/GitHub/Agent-Skills/skills/pr-follow-through/SKILL.md): existing pull/merge request feedback, CI fixes, branch updates, current-head readiness, and bounded continuation. Publication, communication, monitoring, merging, and deployment retain their actual authorization boundaries.

Workforce now hands off the exact base/head, acceptance evidence, outstanding findings, and permission scope when follow-through is requested. It does not automatically start monitoring after creating a PR.

## Verification

Executed the shared command successfully:

```sh
/tmp/agent-skills-metadata-venv/bin/python -B scripts/check.py
```

**181 tests passed:** 33 root packaging/evaluation tests, 81 epic tests, 45 workforce tests, and 22 wizard tests. Bash syntax and ShellCheck passed. All 14 skill packages passed both repository metadata validation and the skill-creator validator. All 14 portable manifests, containing 32 cases, validated. The temporary development virtual environment holds PyYAML; system Python and runtime skill dependencies were not changed.

Four independent fresh-context GPT evaluations were run against prepared disposable fixtures:

1. **Review without a spec:** found and reproduced a concurrency regression; supplied source stayed unchanged.
2. **Bug investigation:** reproduced zero-limit behavior, observed a new regression fail, made a bounded fix, and passed all four fixture tests.
3. **PR review/CI fix:** reproduced the CI failure, fixed the local behavior with acceptance coverage, and passed all three fixture tests without publication or readiness claims.
4. **Changed PR head:** rejected old successful checks and a dismissed approval as proof of current readiness, and disclosed unavailable live monitoring.

The lead inspected these outputs and reran the seven changed-fixture tests. Native-agent evidence is stored locally under the ignored `evals/results/2026-11-12-forward/` directory, including copied case hashes, reports, and separate grading notes. These were native sessions, not executions through the CLI adapter.

An independent helper review found one custom-heading drift defect; the lead corrected it and added two regressions before the final integrated test run.

## Remaining validation limits

The full 32-case behavioral suite and without-skill baseline comparison were not executed. These four cases establish useful forward behavior, not universal productivity gains. Cross-provider and cross-platform execution, live GitHub/other-forge APIs, real cancellation/monitoring, and real publication were not tested. The evaluation harness and run-state helper explicitly distinguish recorded observations from verified external state.

Historical issue bodies do not identify ownership of arbitrary trailing custom headings; removing such a section requires a complete body-diff inspection. Apply never edits those bodies automatically. Dotenv formats differ, so the wizard documents its supported subset and requires verification against the target project's consumer.

To repeat local checks, install [development requirements](/Users/jamallyons/Developer/GitHub/Agent-Skills/requirements-dev.txt) in a virtual environment, then run [scripts/check.py](/Users/jamallyons/Developer/GitHub/Agent-Skills/scripts/check.py). See [evaluation guidance](/Users/jamallyons/Developer/GitHub/Agent-Skills/docs/evaluation.md) for adapters and honest grading.
