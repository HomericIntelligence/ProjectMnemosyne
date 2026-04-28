#!/usr/bin/env bash
# Verify no symlinks escape the repository root and none are broken.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)"
ROOT="$(cd "$ROOT" && pwd -P)"
fail=0

while IFS= read -r -d '' link; do
  target="$(readlink -- "$link")"
  case "$target" in
    /*) abs="$target" ;;
    *)  abs="$(cd "$(dirname -- "$link")" && pwd -P)/$target" ;;
  esac
  resolved="$(readlink -m -- "$abs")"
  case "$resolved" in
    "$ROOT"|"$ROOT"/*) ;;
    *) echo "ERROR: symlink escapes repo: $link -> $target"; fail=1 ;;
  esac
  if [ ! -e "$link" ]; then
    echo "ERROR: broken symlink: $link -> $target"; fail=1
  fi
done < <(find "$ROOT" -path "$ROOT/.git" -prune -o -type l -print0)

[ "$fail" -eq 0 ] && echo "symlink-check: OK" || exit 1
