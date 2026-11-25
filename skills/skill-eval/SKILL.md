---
name: skill-eval
description: Measure whether skills earn their tokens by running paired with-skill and without-skill baseline comparisons, grading the outputs blind against each case's expected outcome, and reporting pass-rate deltas, elapsed time, and reported tokens. Use when the user asks to evaluate their skills, run evals, benchmark skills, check whether a skill helps or is worth its cost, or compare agent behavior with and without a skill. Do not use for repository unit tests or metadata checks (run scripts/check.py), or for revising a skill after one failed session (skill-retro).
---

# Skill evaluation

Measure a skill against the same agent without it. Evidence comes from recorded runs and grades; never fill a gap with an estimate. The harness is `scripts/evaluate.py` in the skills repository; read `docs/evaluation.md` there for exact arguments.

## Scope the comparison

1. Identify the skills and cases. Default to every case in each skill's `evals/evals.json`; when the user limits cost, keep at least one ordinary case and one boundary or negative case per skill. Run `evaluate.py validate` first.
2. Choose one adapter, host, model, and timeout for every run. Example adapters live in `scripts/adapters/`; check their flags against the installed CLI's `--help` before use. If no agent CLI or adapter is available, stop and say so; do not simulate runs yourself.
3. Confirm the run budget with the user before executing when it exceeds a handful of sessions; each case costs two agent sessions plus grading.
4. Set the isolation. Comparisons must live outside the skills tree. Installed copies of the skill under test, or any user skills, contaminate the baseline: disable skill loading or use a clean profile for both variants. Deny live accounts, network writes, and publication; separate directories are not a sandbox.

## Run both variants

For each case: `prepare` into a fresh directory, then `run` `without_skill` and `with_skill` with identical adapter, host, and model. Alternate which variant goes first across cases. Record `launch_failed`, `failed`, or `timed_out` honestly; never rerun a variant in place—prepare a fresh comparison and keep both records.

## Grade blind

1. Run `blind` to copy both variants' outputs under shuffled labels A/B. The packet omits the skill snapshot and prompts; the key stays in `blind-key.json`.
2. Prefer a fresh grader (a separate session or subagent) that receives only the packet and `case.json`'s `prompt` and `expected_output`. When you must grade yourself, still grade from the packet and do not open the key or variant directories until both labels are graded.
3. Split `expected_output` into short, checkable assertions and use the same assertion ids for A and B. Mark each `pass`, `partial`, or `fail` with evidence quoted or cited from the artifacts. A clean exit code is not a pass; missing tool traces are not proof an action was avoided. List limitations (missing traces, ambiguous expectations, timeouts).
4. Write the note as JSON and record it with `grade --label A|B --note note.json`. The harness refuses variants that never ran and mismatched assertion sets.

## Report and recommend

Run `report <comparison dirs> --out <prefix>` and read both the Markdown and JSON. Then give a recommendation per skill:

- **Earns its tokens**: positive score delta across paired cases with no boundary-case regressions; note any token or time cost the adapter actually reported.
- **Needs fixes**: zero or negative delta, regressions on negative cases, or wins only from over-reach. Name the failing assertions and the instruction likely responsible.
- **Inconclusive**: few paired cases, ungraded runs, mismatched host/model, or several skill snapshots. Say what more evidence would settle it.

Keep claims proportional to the sample: one case per variant is an anecdote. Do not report tokens the adapter did not record or infer them from time. Keep comparison directories local; they can contain private prompts and outputs. Finish with commands run, comparison paths, the report path, recommendations, and limitations.
