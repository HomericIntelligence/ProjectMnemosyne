# Session Notes: dockerfile-extras-validation

## Context

- **Date**: 2026-03-02
- **Project**: ProjectScylla
- **Issue**: #1204 — Validate EXTRAS group names at Docker build time
- **PR**: #1306
- **Branch**: `1204-auto-impl`

## Problem

The Layer 2 `RUN python3 -c` snippet in `docker/Dockerfile` silently ignored unknown
group names in the `EXTRAS` build-arg. A typo like `EXTRAS=analyysis` produced only
runtime deps with no warning, making it impossible to detect build mistakes.

## Solution

Extended the existing snippet with a validation step using Python set arithmetic:

```python
unknown = extras - valid
(print(f'ERROR: Unknown EXTRAS group(s): {sorted(unknown)}. Valid: {sorted(valid)}', file=sys.stderr) or sys.exit(1)) if unknown else None
```

The single-expression pattern (`(print(...) or sys.exit(1)) if cond else None`) was chosen
because multi-line `if` blocks are awkward inside a Dockerfile `RUN python3 -c "..."` continuation.

## Files Changed

- `docker/Dockerfile` — extended Layer 2 RUN snippet; updated comment block
- `tests/unit/scripts/test_dockerfile_extras_validation.py` — 8 new static regression tests

## Test Results

- 8 new tests: all pass
- 3593 total tests: 3592 passed, 1 skipped
- Coverage: 67.46% (threshold: 9%)
- Pre-commit: all hooks pass (ruff, mypy, shellcheck, markdownlint, etc.)

## Manual Verification (expected behavior, not run in CI)

| Command | Expected |
|---------|----------|
| `docker build .` | Succeeds (no extras) |
| `docker build --build-arg EXTRAS=analysis .` | Succeeds |
| `docker build --build-arg EXTRAS=analyysis .` | Fails: `ERROR: Unknown EXTRAS group(s): ['analyysis']. Valid: ['analysis', 'dev']` |
| `docker build --build-arg EXTRAS=analysis,dev .` | Succeeds |