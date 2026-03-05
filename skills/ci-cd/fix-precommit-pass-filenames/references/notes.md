# Session Notes: fix-precommit-pass-filenames

## Context

- **Issue**: #3154 — Fix ruff pre-commit hooks to use pass_filenames: true
- **Branch**: 3154-auto-impl
- **PR**: #3347
- **Date**: 2026-03-05

## Problem

`.pre-commit-config.yaml` had two ruff hooks with `pass_filenames: false` and hardcoded
directory args in `entry`. This meant every commit triggered a full scan of `scripts/`,
`examples/`, `tests/`, and `tools/` regardless of which files actually changed.

## Root Cause

When `pass_filenames: false`, pre-commit calls the entry command with no file arguments.
The hook then uses its own hardcoded paths. The `files:` pattern only controls which staged
files trigger the hook — it does not restrict what the hook scans.

With `pass_filenames: true`, pre-commit appends the matching staged files to the entry
command, enabling true incremental checking.

## Exact Change

File: `.pre-commit-config.yaml`

```diff
- entry: pixi run ruff format scripts/ examples/ tests/ tools/
+ entry: pixi run ruff format
- pass_filenames: false
+ pass_filenames: true

- entry: pixi run ruff check --fix scripts/ examples/ tests/ tools/
+ entry: pixi run ruff check --fix
- pass_filenames: false
+ pass_filenames: true
```

## Verification

```
$ pixi run pre-commit run --all-files
Ruff Format Python.......................................................Passed
Ruff Check Python........................................................Passed
```

All other hooks also passed (Mojo Format hook failed due to GLIBC on Debian 10 — pre-existing).

## Time taken

~5 minutes total: read config, make 4-line edit, run verification, commit, push, create PR.
