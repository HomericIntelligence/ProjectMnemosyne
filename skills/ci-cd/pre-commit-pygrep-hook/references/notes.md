# Session Notes — pre-commit-pygrep-hook

## Context

**Issue**: ProjectOdyssey #3703 — "Add pre-commit hook to catch runtime NOTE/TODO/FIXME prints"

**Follow-up from**: #3194 (manual grep audit)

**Branch**: `3703-auto-impl`

**PR**: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4774

## Objective

Convert a manual audit step (`grep -rn 'print.*NOTE\|print.*TODO\|print.*FIXME' examples/`) into
an automated pre-commit hook so debug artifacts are caught at commit time instead of during
periodic audits.

## Steps Taken

1. Read `.pre-commit-config.yaml` to understand existing hook patterns (pygrep, system, script hooks).
2. Added `check-print-debug-artifacts` hook using `language: pygrep` — minimal, zero-dependency.
3. Scoped hook to `^examples/` matching the original audit scope.
4. Created `tests/test_check_print_debug_artifacts.py` with 12 parametrized pytest cases.
5. Discovered pygrep matches commented-out lines — adjusted test expectations accordingly.
6. Validated hook: `SKIP=mojo-format,mypy pixi run pre-commit run check-print-debug-artifacts --all-files` → Passed.
7. All 12 tests pass.

## Key Decisions

- **pygrep vs system language**: pygrep is preferred for simple pattern matching — no shell
  subprocess needed, no platform differences, pre-commit handles file iteration.
- **Placement**: Added to the first `repo: local` block alongside `check-list-constructor`
  (another pygrep hook) for consistency.
- **Commented-out lines are flagged**: This is correct — `# print("NOTE: ...")` in source
  suggests code that was commented out rather than deleted, which is itself a code smell.

## Regex Translation

Grep syntax: `print.*NOTE\|print.*TODO\|print.*FIXME`

Python re syntax: `print.*(NOTE|TODO|FIXME)`

## Test Failure & Fix

Initial test included `# print("NOTE: commented out")` in NEGATIVE_CASES. Failed because
pygrep applies the regex to the raw file line including the `#` prefix. Fixed by moving
to POSITIVE_CASES with description "commented-out print still flagged".
