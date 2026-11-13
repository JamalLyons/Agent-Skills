# Checking and evaluating skills

Run the local package/helper checks from the repository root (or use the script's absolute path from another working directory):

```sh
python3 -B scripts/check.py
```

Use the repository's development dependencies when a metadata check requires them (`python3 -m pip install -r requirements-dev.txt`). The runner discovers each root/skill `tests/` directory and starts a separate Python process, preventing imports from similarly named skill modules from contaminating another suite. It also validates portable JSON evaluation manifests and runs Bash syntax checks and ShellCheck when installed. Missing optional tools are reported. CI installs the check tools and runs the same command. Passing these checks does not establish agent adherence.

## Portable behavioral cases

Each `skills/<name>/evals/evals.json` defines `skill_name` and an `evals` list. Every case has a unique `id`, realistic `prompt`, human-readable `expected_output`, and optional `files` relative to its skill directory. Fixture files must stay inside that skill. These pinned inputs avoid depending on mutable live issue bodies. The older workforce YAML cases/catalogs remain additional reference specifications; the portable runner does not claim to execute their host-specific traces.

Validate every discovered manifest, including newly added skills:

```sh
python3 scripts/evaluate.py validate
```

Prepare a fresh comparison:

```sh
python3 scripts/evaluate.py prepare skills/code-review/evals/evals.json \
  --case correctness-without-spec --out /tmp/code-review-comparison-1
```

This produces separate `without_skill/` and `with_skill/` directories, each containing a fresh `workspace/`, `prompt.txt`, and `outputs/`. Both receive identical fixture bytes. Only the skill variant receives `_skills/` with instructions and resources; evals, graders, tests, and expected answers are excluded from that snapshot. Sibling skill resources are included to preserve relative references. `case.json` outside the workspaces records fixture/skill hashes, the original prompt, the manifest hash, and expected outcomes for a separate grader. Never include `case.json` in the evaluated agent's context.

## Run through your agent's adapter

The harness does not select a provider, model, API, or commercial runtime. Supply an executable adapter that starts a **fresh agent session**, reads the supplied prompt, works only in its current disposable directory, and writes useful artifacts/tool traces into the output directory. Choose its permissions and network restrictions explicitly. An adapter can be a small wrapper around any supported agent CLI; flags differ by host, so none are guessed here.

```sh
python3 scripts/evaluate.py run /tmp/code-review-comparison-1 \
  --variant with_skill --host YOUR_HOST --model YOUR_MODEL \
  --adapter-json '["/absolute/path/to/your-adapter", "--prompt", "{prompt_file}", "--output", "{output_dir}"]'
```

Run the same adapter and model with `--variant without_skill`. Available argv placeholders are `{prompt_file}`, `{output_dir}`, `{workspace}`, and `{variant}`. Arguments are passed directly without shell evaluation. The adapter must include `{prompt_file}`. Use `--timeout` for a finite deadline (default 300 seconds, maximum 1,800). Standard output/error, exit code, elapsed time, host/model labels, and the exact argv are captured per variant. A variant cannot be executed twice; prepare a fresh comparison for a repeat. POSIX timeouts kill only the process group created for that adapter; on other systems only the adapter process is terminated, so host-specific descendant cleanup may be necessary.

An exit code of zero means **the adapter completed**, not that the skill passed. `semantic_grade` remains `null`. Inspect actual artifacts and recorded tool actions against `expected_output`, then record a separate grading note with evidence, limitations, and pass/fail/partial decisions for individual assertions. Compare correctness, unnecessary questions, actions, elapsed time, and tokens only when the adapter actually reports them. Do not infer token cost from elapsed time or treat missing tool traces as proof that no prohibited action happened.

## Isolation and authority

Separate workspaces and fresh processes reduce context carryover. They are **not a security sandbox**, and task instructions do not disable credentials or network access. Run adapters with a host/container permission configuration that denies live accounts, network mutations, and publication; use mocked tool responses for trackers and delegation. If those controls are unavailable, use a read-only reasoning case or stop rather than run a live backlog scenario. Fixtures, prompts, stdout, and adapter artifacts can contain private information in other applications; use synthetic data, keep results local by default, and review them before sharing.

The checked-in cases cover ordinary use and boundary/negative behavior. They are specifications until actual sessions and evidence have been recorded. This repository's harness unit tests use only local stub executables; those tests establish preparation/execution behavior and do not count as model evaluations.
