#!/usr/bin/env bash
# Link every skill in skills/ into the skills directories that agents scan.
#
#   ./install.sh                  link into the default targets (below)
#   ./install.sh --target DIR ... link only into the given directories (repeatable)
#   ./install.sh --dry-run        preview without creating directories or links
#   ./install.sh --replace-links  explicitly replace conflicting foreign symlinks
#
# Default targets:
#   ~/.claude/skills   Claude Code (override with CLAUDE_SKILLS_DIR)
#   ~/.agents/skills   shared Agent Skills folder read by skill-capable agents
#                      (override with AGENT_SKILLS_DIR)
#
# Each skill is exposed through a symlink. Re-running preserves correct links,
# refreshes links owned by this repository, and prunes its broken links. Foreign
# links require --replace-links; real files/directories are never overwritten.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# Resolve existing directory targets physically, including relative symlinks.
# A broken skill link can still be recognized when its parent directory exists.
link_target() {
  local target parent
  target=$(readlink "$1") || return 1
  [[ "$target" == /* ]] || target="$(dirname "$1")/$target"
  if [[ -d "$target" ]]; then
    (cd "$target" && pwd -P)
  else
    parent=$(cd "$(dirname "$target")" 2>/dev/null && pwd -P) || return 1
    printf '%s/%s\n' "$parent" "$(basename "$target")"
  fi
}

owned_target() {
  case "$1" in "$REPO"/skills/*) return 0 ;; *) return 1 ;; esac
}

targets=()
dry_run=0
replace_links=0
while [ $# -gt 0 ]; do
  case "$1" in
    --target) [ $# -ge 2 ] && [ -n "$2" ] || { echo "--target needs a directory" >&2; exit 2; }
              targets+=("$2"); shift 2 ;;
    --dry-run) dry_run=1; shift ;;
    --replace-links) replace_links=1; shift ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
if [ ${#targets[@]} -eq 0 ]; then
  targets=("${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}" "${AGENT_SKILLS_DIR:-$HOME/.agents/skills}")
fi

status=0
kept=0
linked=0
replaced=0
pruned=0
collisions=0
for DEST in "${targets[@]}"; do
  echo "$DEST"
  if { [ -e "$DEST" ] || [ -L "$DEST" ]; } && [ ! -d "$DEST" ]; then
    echo "  skip    destination exists and is not a directory" >&2
    collisions=$((collisions + 1)); status=1
    continue
  fi
  if [ ! -d "$DEST" ]; then
    if [ "$dry_run" -eq 1 ]; then echo "  would create directory"
    else mkdir -p "$DEST"; fi
  fi

  for link in "$DEST"/*; do
    [ -L "$link" ] && [ ! -e "$link" ] || continue
    resolved=$(link_target "$link" || true)
    if owned_target "$resolved"; then
      if [ "$dry_run" -eq 1 ]; then echo "  would prune   $(basename "$link")"
      else rm "$link"; echo "  prune   $(basename "$link")"; fi
      pruned=$((pruned + 1))
    fi
  done

  for dir in "$REPO"/skills/*/; do
    dir="${dir%/}"
    [ -f "$dir/SKILL.md" ] || continue
    name="$(basename "$dir")"
    link="$DEST/$name"
    if [ -L "$link" ]; then
      resolved=$(link_target "$link" || true)
      if [ "$dry_run" -eq 1 ] && [ ! -e "$link" ] && owned_target "$resolved"; then
        # The previewed prune above removes this entry before installation.
        echo "  would link    $name -> $dir"
        linked=$((linked + 1))
        continue
      fi
      if [ "$resolved" = "$dir" ]; then
        echo "  ok      $name"
        kept=$((kept + 1))
        continue
      fi
      if ! owned_target "$resolved" && [ "$replace_links" -ne 1 ]; then
        echo "  skip    $name: foreign symlink preserved; use --replace-links to replace it" >&2
        collisions=$((collisions + 1)); status=1
        continue
      fi
      if [ "$dry_run" -eq 1 ]; then echo "  would relink  $name -> $dir"
      else ln -sfn "$dir" "$link"; echo "  relink  $name -> $dir"; fi
      replaced=$((replaced + 1))
    elif [ -e "$link" ]; then
      echo "  skip    $name: $link exists and is not a symlink; move it aside and re-run" >&2
      collisions=$((collisions + 1)); status=1
    else
      if [ "$dry_run" -eq 1 ]; then echo "  would link    $name -> $dir"
      else ln -s "$dir" "$link"; echo "  link    $name -> $dir"; fi
      linked=$((linked + 1))
    fi
  done
done
if [ "$dry_run" -eq 1 ]; then echo "Dry run: no files changed. Counts describe planned actions."; fi
printf 'Summary: %s kept, %s links, %s replacements, %s pruned, %s collisions\n' \
  "$kept" "$linked" "$replaced" "$pruned" "$collisions"
exit "$status"
