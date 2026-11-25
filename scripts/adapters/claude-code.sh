#!/usr/bin/env bash
# Example adapter (not a requirement) for scripts/evaluate.py run: one fresh, headless Claude Code session.
# Usage: claude-code.sh PROMPT_FILE OUTPUT_DIR
# The harness sets the working directory to the variant workspace.
# Flags checked against `claude --help` for Claude Code 2.1.331; recheck on other versions.
# Environment: EVAL_MODEL (optional --model), EVAL_PERMISSION_MODE (default acceptEdits).
# This is not a sandbox: Bash can still reach the network. Run it inside a container or VM
# without live credentials when a case could cause external effects.
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 PROMPT_FILE OUTPUT_DIR" >&2
  exit 2
fi
prompt_file=$1
output_dir=$2

args=(-p --output-format json --no-session-persistence
  --permission-mode "${EVAL_PERMISSION_MODE:-acceptEdits}"
  # Installed user skills would contaminate the without_skill baseline; the with_skill
  # variant reads its snapshot from _skills/ by path, so it does not need skill loading.
  --disable-slash-commands
  --disallowedTools WebFetch WebSearch)
if [ -n "${EVAL_MODEL:-}" ]; then
  args+=(--model "$EVAL_MODEL")
fi

claude "${args[@]}" < "$prompt_file" > "$output_dir/result.json"

# Copy the final text and reported token usage; leave usage.json absent if not reported.
python3 - "$output_dir" <<'PY'
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
try:
    data = json.loads((out / 'result.json').read_text())
except ValueError:
    sys.exit(0)
(out / 'final.md').write_text(str(data.get('result', '')))
usage = data.get('usage') or {}
tokens = {k: usage.get(k) for k in ('input_tokens', 'output_tokens')}
if all(isinstance(v, int) for v in tokens.values()):
    (out / 'usage.json').write_text(json.dumps(tokens) + '\n')
PY
