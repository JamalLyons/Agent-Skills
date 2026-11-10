#!/usr/bin/env bash
# Print candidate build/test/lint/format commands found in the current repo.
# Run from the repo root. Output is a hint list. Confirm it against the repo docs before relying on it.
set -u

found=0
say() { printf '%-10s %s\n' "$1" "$2"; found=1; }

# Task runners first: they usually wrap everything else.
if [ -f Justfile ] || [ -f justfile ]; then
  if command -v just >/dev/null 2>&1; then
    just --summary 2>/dev/null | tr ' ' '\n' | grep -Ei '^(build|test|check|lint|fmt|format|ci|verify)' | while read -r r; do say just "just $r"; done
  else
    grep -Eo '^[a-zA-Z_-]+' Justfile justfile 2>/dev/null | grep -Ei '^(build|test|check|lint|fmt|format|ci|verify)' | while read -r r; do say just "just $r"; done
  fi
  found=1
fi
if [ -f Makefile ]; then
  grep -Eo '^[a-zA-Z_-]+:' Makefile | tr -d ':' | grep -Ei '^(build|test|check|lint|fmt|format|ci|verify)' | while read -r r; do say make "make $r"; done
  found=1
fi
if [ -f package.json ]; then
  pm=npm; [ -f pnpm-lock.yaml ] && pm=pnpm; [ -f yarn.lock ] && pm=yarn; [ -f bun.lockb ] || [ -f bun.lock ] && pm=bun
  if command -v node >/dev/null 2>&1; then
    node -e 'const s=require("./package.json").scripts||{};for(const k of Object.keys(s))if(/^(build|test|lint|typecheck|check|format|fmt)/i.test(k))console.log(k)' 2>/dev/null | while read -r r; do say "$pm" "$pm run $r"; done
  fi
  found=1
fi
[ -f Cargo.toml ] && { say cargo "cargo build"; say cargo "cargo test"; say cargo "cargo clippy -- -D warnings"; say cargo "cargo fmt --check"; }
[ -f go.mod ] && { say go "go build ./..."; say go "go test ./..."; say go "go vet ./..."; }
{ [ -f pyproject.toml ] || [ -f setup.py ]; } && { say python "pytest"; grep -q ruff pyproject.toml 2>/dev/null && say python "ruff check ."; }
[ -f Package.swift ] && { say swift "swift build"; say swift "swift test"; }
if [ -f CMakePresets.json ]; then
  say cmake "cmake --list-presets  # then: cmake --preset <p> && cmake --build --preset <p> && ctest --preset <p>"
elif [ -f CMakeLists.txt ]; then
  say cmake "cmake -S . -B build && cmake --build build && ctest --test-dir build"
fi
[ -f .clang-format ] && say format "clang-format --dry-run --Werror <changed files>"
[ -f .pre-commit-config.yaml ] && say hooks "pre-commit run --all-files"
ls .github/workflows/*.y*ml >/dev/null 2>&1 && say ci "see .github/workflows/: CI is the ground truth for what must pass"

[ "$found" = 0 ] && echo "No known build manifests found. Check README/CONTRIBUTING for how to build and test."
exit 0
