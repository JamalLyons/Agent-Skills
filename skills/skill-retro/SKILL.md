---
name: skill-retro
license: MIT
description: Run a retrospective on one real agent session that used a skill. Compare what the agent actually did against that skill's SKILL.md, find where the instructions caused or failed to prevent a problem, and propose a minimal skill diff plus a portable eval case that would have caught it. Use when the user says a skill didn't work well, the agent ignored or misread a skill, asks to improve a skill from this session, or asks for a retro on this run, transcript, or handoff. Do not use to measure a skill across many cases or compare with/without-skill runs (skill-eval), for general code or PR review (code-review), or to debug the user's product code (bug-investigation).
---

# Skill retro

Turn one observed session into a small, verified improvement to a skill and a regression eval.

## Inputs

- The session: the current conversation, or a transcript/handoff file path the user names. Read all of it before judging.
- The skill name(s) used. If unstated, infer from the transcript and confirm only when several are plausible.
- Locate the skill **source**. Installed copies are often symlinks (for example `~/.claude/skills/<name>` or `~/.agents/skills/<name>`); resolve them (`readlink -f`, `realpath`) to the source repository and edit there. Never edit an installed copy or a cache. If no writable source exists, report the proposed diff instead.
- Read the source repository's contribution and evaluation docs and its checks before editing.

## Evidence first

Build a timeline of the relevant moments. For each problem record:

1. The exact transcript quote (turn or line) showing what the agent did.
2. The exact SKILL.md lines (path and line numbers) that applied, or the absence of any.
3. A classification:
   - **Skill caused it**: ambiguous, missing, contradictory, wrongly triggered, or bloated instructions led to the action or failed to prevent it (missed trigger, ambiguous step, wasted context, unsafe action, wrong tool, skipped verification).
   - **Model/host error**: the skill was clear and the agent ignored it, or a tool/host failure occurred that wording could not prevent.
   - **User changed requirements**: the request moved after the skill was followed correctly.

Propose edits only for "skill caused it". For the other two, write a one-line note and no edit. When a clear instruction was ignored, do not repeat it louder; consider only whether placement or length hid it. Do not speculate past the evidence; mark inferences as inferences.

## Edit discipline

- Make the smallest change that would have prevented the observed failure. One failure, one targeted fix; no drive-by rewrites.
- Preserve provider neutrality: no host-specific tool names, models, or paths unless the skill is already host-specific.
- Do not bloat. If a section must grow, move detail into `references/` and link it from SKILL.md.
- Re-read the frontmatter `description`: confirm it still triggers for the observed request and does not now overlap a sibling skill. Fix a missed trigger in the description, not the body.
- Check sibling skills in the same repository for contradictions with the new wording.

## Regression eval

Always add or adjust one case in the skill's eval manifest (for agentskills.io-style repos, `evals/evals.json`: unique `id`, realistic `prompt`, observable `expected_output`, `files` under `evals/fixtures/`) that reproduces the failure and would fail under the old wording.

- Fixtures must be synthetic. Never copy a raw transcript into a fixture.
- Redact secrets, tokens, keys, emails, names, internal hostnames, and other PII from anything you quote or store; replace with obvious placeholders such as `<REDACTED_TOKEN>` or `example.invalid`. Also redact them in the retro report.
- If no edit was justified, an eval is still allowed when it guards the correct behavior; say so.

## Verify

Run the source repository's checks (for example `scripts/check.py` and `scripts/evaluate.py validate`). Report actual commands and results; distinguish pre-existing failures from new ones. Do not claim the eval passes against an agent unless you actually ran one.

Commit, push, or open a pull request only when the user asks.

## Report

Keep it short:

1. **What happened**: timeline with quoted evidence.
2. **Root cause in the skill**: the lines and why they misled, or "none — not a skill problem" with the classification.
3. **Change**: the diff or its location.
4. **New eval**: case id, fixture paths, and what it checks.
5. **Not fixed and why**: model/host errors, requirement changes, out-of-scope ideas, and checks not run.
