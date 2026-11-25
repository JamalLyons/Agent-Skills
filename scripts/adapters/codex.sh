#!/usr/bin/env bash
# Example adapter (not a requirement) for scripts/evaluate.py run: one fresh, non-interactive Codex session.
# Usage: codex.sh PROMPT_FILE OUTPUT_DIR
# The harness sets the working directory to the variant workspace.
# Flags checked against `codex exec --help` for codex-cli 0.172.0; recheck on other versions.
# The JSONL usage event shape (turn.completed.usage) is not documented by --help; verify it.
# Environment: EVAL_MODEL (optional --model), EVAL_SANDBOX (default workspace-write).
# Skills installed under CODEX_HOME can load in both variants; point CODEX_HOME at a clean
# directory with only auth configured to keep the without_skill baseline uncontaminated.
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 PROMPT_FILE OUTPUT_DIR" >&2
  exit 2
fi
prompt_file=$1
output_dir=$2

args=(exec --cd "$PWD" --sandbox "${EVAL_SANDBOX:-workspace-write}" --ephemeral
  --skip-git-repo-check --json --output-last-message "$output_dir/final.md")
if [ -n "${EVAL_MODEL:-}" ]; then
  args+=(--model "$EVAL_MODEL")
fi

codex "${args[@]}" - < "$prompt_file" > "$output_dir/events.jsonl"

# Sum reported token usage; leave usage.json absent if no usage events were reported.
python3 - "$output_dir" <<'PY'
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
totals, seen = {'input_tokens': 0, 'output_tokens': 0}, False
for line in (out / 'events.jsonl').read_text().splitlines():
    try:
        event = json.loads(line)
    except ValueError:
        continue
    usage = event.get('usage') if isinstance(event, dict) and event.get('type') == 'turn.completed' else None
    if isinstance(usage, dict) and all(isinstance(usage.get(k), int) for k in totals):
        seen = True
        for k in totals:
            totals[k] += usage[k]
if seen:
    (out / 'usage.json').write_text(json.dumps(totals) + '\n')
PY
