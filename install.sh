#!/usr/bin/env bash
# Link every skill in skills/ into the skills directories that agents scan.
#
#   ./install.sh                  link into the default targets (below)
#   ./install.sh --target DIR ... link only into the given directories (repeatable)
#
# Default targets:
#   ~/.claude/skills   Claude Code (override with CLAUDE_SKILLS_DIR)
#   ~/.agents/skills   shared Agent Skills folder read by Codex, Cursor and Gemini CLI
#                      (override with AGENT_SKILLS_DIR)
#
# Agents only discover <dir>/<name>/SKILL.md one level deep, so each skill
# folder in this repo is exposed through a symlink. Idempotent: re-running
# refreshes links, prunes broken links into this repo (renamed or deleted
# skills), and never overwrites a real directory.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

targets=()
while [ $# -gt 0 ]; do
  case "$1" in
    --target) [ $# -ge 2 ] || { echo "--target needs a directory" >&2; exit 2; }
              targets+=("$2"); shift 2 ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
if [ ${#targets[@]} -eq 0 ]; then
  targets=("${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}" "${AGENT_SKILLS_DIR:-$HOME/.agents/skills}")
fi

status=0
for DEST in "${targets[@]}"; do
  echo "$DEST"
  mkdir -p "$DEST"

  for link in "$DEST"/*; do
    [ -L "$link" ] && [ ! -e "$link" ] || continue
    case "$(readlink "$link")" in
      "$REPO"/skills/*) rm "$link"; echo "  prune   $(basename "$link")" ;;
    esac
  done

  for dir in "$REPO"/skills/*/; do
    dir="${dir%/}"
    [ -f "$dir/SKILL.md" ] || continue
    name="$(basename "$dir")"
    link="$DEST/$name"
    if [ -L "$link" ]; then
      if [ "$(readlink "$link")" = "$dir" ]; then
        echo "  ok      $name"
        continue
      fi
      ln -sfn "$dir" "$link"
      echo "  relink  $name -> $dir"
    elif [ -e "$link" ]; then
      echo "  skip    $name: $link exists and is not a symlink; move it aside and re-run" >&2
      status=1
    else
      ln -s "$dir" "$link"
      echo "  link    $name -> $dir"
    fi
  done
done
exit "$status"
