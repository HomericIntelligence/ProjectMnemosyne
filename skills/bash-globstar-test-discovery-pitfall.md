---
name: bash-globstar-test-discovery-pitfall
description: "Test runners that use `for f in dir/**/*.ext` silently skip files at depth >=3 without `shopt -s globstar`. Use when: (1) writing a bash loop over recursive globs, (2) test count is suspiciously low, (3) coverage metrics drop after refactor."
category: testing
date: 2026-05-11
version: "1.0.0"
verification: verified-ci
user-invocable: false
tags: [bash, globstar, test-discovery, find, mapfile, justfile, recursive-glob, silent-failure]
---

# Bash Globstar Test Discovery Pitfall

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-11 |
| **Objective** | Prevent test runners from silently skipping files at depth >=3 when iterating with `dir/**/*.ext` |
| **Outcome** | Success — replaced glob with `find \| mapfile`; coverage went from 41/298 tests (~14%) to 298/298 (100%) |
| **Verification** | verified-ci |

## When to Use

- Writing a bash `for` loop over a recursive glob like `tests/**/*.mojo`, `src/**/*.py`, or any `**/*` pattern
- Test count, file count, or coverage metric is suspiciously low after a refactor that "should not have changed anything"
- A test suite "passes" but a deliberately-failing test at depth >=3 doesn't break the build
- `find dir -name '*.ext' | wc -l` returns N files but the loop iterates far fewer
- Iterating over files in a justfile, Makefile, or CI script that runs under bash without explicit shell options

## Verified Workflow

### Quick Reference

```bash
# WRONG — silently skips files at depth >=3 (no globstar enabled)
for test_file in tests/**/*.mojo; do
    [[ "$(basename "$test_file")" == "__init__.mojo" ]] && continue
    mojo run "$test_file" || exit 1
done

# WRONG (subtle) — works only if `shopt -s globstar` is active in this shell
shopt -s globstar
for test_file in tests/**/*.mojo; do
    # Works here, but future contributors copying the loop elsewhere lose the shopt
done

# RIGHT — `find` walks the tree recursively regardless of bash options
mapfile -t test_files < <(
    find tests -name "test_*.mojo" \
        -not -path "*/__init__.mojo" \
        -not -path "tests/helpers/fixtures.mojo" \
        -not -path "tests/helpers/utils.mojo" \
        -not -path "tests/conftest.mojo" \
        | sort
)
test_count=${#test_files[@]}
for test_file in "${test_files[@]}"; do
    mojo run "$test_file" || exit 1
done
```

### Detailed Steps

1. **Identify the symptom**: Compare expected to actual file count. Run `find <dir> -name '<pattern>' | wc -l` and compare to the loop's iteration count (add `echo "Processing: $f"` to the loop body and count lines). If they differ, recursion is broken.

2. **Confirm the cause**: Check whether `shopt -s globstar` is active in the shell running the loop. Justfiles, Makefiles, CI scripts, and remote shells (ssh, podman exec) often run a fresh bash without it. In a fresh bash, `**` is equivalent to `*` — it matches only the immediate level.

3. **Replace the glob with `find` + `mapfile`**:
   - Use `find <root> -name '<pattern>'` for the recursive walk. `find` does not depend on bash shell options.
   - Make exclusions explicit with `-not -path 'glob'`. This is auditable in the recipe itself, not buried in `[[ ]]` checks inside the loop.
   - Pipe through `sort` for deterministic ordering.
   - Use `mapfile -t array < <(...)` to read into an array. Process substitution `< <(...)` (not pipe) keeps `mapfile` in the parent shell so the array is visible after the redirect closes.

4. **Iterate the array with quoted expansion**: `for f in "${array[@]}"` (with quotes) handles whitespace and special characters in paths correctly. Raw `for f in $variable` splits on IFS and breaks on spaces.

5. **Verify**: Print `${#test_files[@]}` before the loop and confirm it matches `find ... | wc -l`. Add a deliberately-failing test at depth >=3 (e.g., `tests/a/b/c/test_canary.mojo`) and confirm the runner now reports it as failed.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `for f in tests/**/*.mojo` (no shopt) | Used `**` directly assuming bash recurses by default | Bash treats `**` as `*` without `shopt -s globstar`; only matches depth 2 (`tests/<file>`). Silent — produces some matches, so the loop "works" | `**` is opt-in in bash; never assume it recurses |
| `shopt -s globstar` at top of recipe | Enabled globstar then iterated `tests/**/*.mojo` | Functional in that recipe, but introduces a footgun: future contributors copy the loop pattern elsewhere without copying the shopt and silently regress | Encode the recursion in the command (`find`), not in shell state |
| `find ... \| while read f; do ...; done` | Piped find output into a while-read loop | The `\|` creates a subshell — counters incremented inside (`(( count++ ))`) don't propagate to the parent; per-file exit codes are masked by the pipe's exit status | Use `mapfile -t arr < <(find ...)` with process substitution so iteration stays in the parent shell |
| `for f in $(find ...)` | Command substitution into unquoted loop | Splits on IFS — breaks on paths containing spaces or special characters | `mapfile` + `"${arr[@]}"` is whitespace-safe |

## Results & Parameters

**Root cause:** In bash, `**` is a normal glob unless `shopt -s globstar` is enabled. With globstar off (the default), `tests/**/*.mojo` expands as if `**` were `*` — matching exactly two path components, so only files at `tests/<dir>/<file>` are found. Files at `tests/<dir>/<subdir>/<file>` or deeper are silently skipped. The loop still iterates, the script still appears to work, and the bug only surfaces when someone notices coverage is wrong or adds a deliberately-failing deep test that never runs.

**The fix replaces shell-state-dependent recursion with explicit `find`:**

```bash
# Canonical pattern for test discovery in bash scripts/justfiles:
mapfile -t test_files < <(
    find <root_dir> -name '<glob_pattern>' \
        -not -path '<exclusion_1>' \
        -not -path '<exclusion_2>' \
        | sort
)
test_count=${#test_files[@]}
echo "Discovered ${test_count} test files"

for test_file in "${test_files[@]}"; do
    # ... run the test ...
done
```

**Why `find` over `shopt -s globstar`:**

1. `globstar` is a bash-specific feature; sourced scripts, remote shells (ssh/podman exec), and non-bash sh implementations may not have it.
2. The filter set is explicit in the `find` command — readable in the recipe, not implicit in shell state.
3. `find -not -path` exclusions are auditable in one place; globstar-based exclusions require multiple `[[ ]]` checks inside the loop.
4. `mapfile` + quoted array expansion handles whitespace in paths correctly; raw `for ... in $glob` does not.

**Verified on:** HomericIntelligence/ProjectOdyssey PR #5389 (2026-05-11). Justfile test recipe walked `tests/**/*.mojo` and ran 41 of 298 test files (~14%). The recipe's summary printed "298 tests" from an unrelated count, masking the gap. After replacing the glob with `find | mapfile`, coverage went from 41/298 to 298/298 under `--Werror`.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/ProjectOdyssey | PR #5389 justfile test recipe | `tests/**/*.mojo` matched only 41/298 files; replaced with `find -name 'test_*.mojo' \| mapfile` to reach 298/298 |
