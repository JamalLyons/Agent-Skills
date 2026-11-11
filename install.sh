#!/usr/bin/env bash
# Link every skill in skills/ into the Claude Code skills directory.
# Claude Code only discovers <skills-dir>/<name>/SKILL.md one level deep,
# so each skill folder in this repo is exposed through a symlink.
# Idempotent: re-running refreshes links and never overwrites real directories.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mkdir -p "$DEST"

status=0
for dir in "$REPO"/skills/*/; do
  dir="${dir%/}"
  [ -f "$dir/SKILL.md" ] || continue
  name="$(basename "$dir")"
  link="$DEST/$name"
  if [ -L "$link" ]; then
    if [ "$(readlink "$link")" = "$dir" ]; then
      echo "ok      $name"
      continue
    fi
    ln -sfn "$dir" "$link"
    echo "relink  $name -> $dir"
  elif [ -e "$link" ]; then
    echo "skip    $name: $link exists and is not a symlink; move it aside and re-run" >&2
    status=1
  else
    ln -s "$dir" "$link"
    echo "link    $name -> $dir"
  fi
done
exit "$status"
