# Session Notes: mypy-hyphenated-dir-per-file

## Context

- **Issue**: HomericIntelligence/ProjectOdyssey#4013
- **PR**: HomericIntelligence/ProjectOdyssey#4856
- **Branch**: `4013-auto-impl`
- **Date**: 2026-03-15

## Objective

Extend mypy type-checking in `.pre-commit-config.yaml` to cover `examples/` in addition to
`scripts/`. The gap was identified because bandit already covers `tools/` and `examples/`, but
mypy only covered `^scripts/.*\.py$`.

## Root Cause Discovery

The naive approach of adding a second mypy hook with `files: ^examples/.*\.py$` and
`pass_filenames: true` fails immediately with:

```
error: Duplicate module named 'download_cifar10'
  (also at 'examples/resnet-cifar10/download_cifar10.py')
note: See https://mypy.readthedocs.io/en/stable/running_mypy.html#mapping-file-paths-to-modules
note: Common resolutions include: a) using `--exclude` to avoid checking one of them,
b) adding `__init__.py` somewhere, c) using `--explicit-package-bases`, or
d) using `--package` or `--module` or `--file`
```

The subdirectories are named `alexnet-cifar10`, `resnet-cifar10` etc. — hyphenated names that
Python cannot use as package identifiers. `--explicit-package-bases` does not help because the
root cause is that two files literally have the same module-qualified name from mypy's perspective.

## Solution

A per-file wrapper script (`scripts/mypy-each-file.py`) that:

1. Receives all the files from pre-commit (via `pass_filenames: true`).
2. Splits the argument list into mypy flags vs file paths.
3. Invokes `python -m mypy <flags> <one-file>` for each file individually.
4. Aggregates exit codes (non-zero if any invocation fails).

The pre-commit hook uses `language: system` and `entry: pixi run python scripts/mypy-each-file.py`
so it runs in the project's pixi environment without needing a separate virtualenv.

## Files Changed

- `.pre-commit-config.yaml`: added `mypy-examples` local hook
- `scripts/mypy-each-file.py`: new wrapper script (55 lines)

## Key Decisions

- Used `language: system` (not `language: python`) to reuse the pixi-managed mypy installation.
- Matched existing mypy flags from the `scripts/` hook for consistency.
- The script returns 0 with a message when called with no files (pre-commit may call with empty
  list in some scenarios, e.g. `--files` filter with no matches).
- No `capture_output` on subprocess — mypy output streams directly to the terminal for visibility.

## What Was Skipped

- Did not add `additional_dependencies` — the `language: system` hook uses pixi's environment
  where mypy and type stubs are already installed.
- Did not use `--package` or `--module` flags — per-file invocation is simpler and more robust.