# Session Notes: dockerfile-tomllib-fallback

## Session Summary

**Date**: 2026-03-02
**Issue**: #1200 (ProjectScylla)
**PR**: #1304 (ProjectScylla)
**Branch**: `1200-auto-impl`

## Objective

Follow up on issue #1138 (documentation-only Python 3.11+ constraint) by implementing an actual
`try/except ImportError` code fallback so the Docker builder stage works on Python 3.10 as well.

## Files Changed

1. `docker/Dockerfile` — Layer 2 RUN replaced with:
   - Pre-install `tomli==2.0.2`
   - Heredoc Python script with `try: import tomllib / except ImportError: import tomli as tomllib`
   - Updated NOTE comment referencing both #1138 and #1200

2. `tests/unit/scripts/test_dockerfile_constraints.py` — Updated:
   - `MIN_PYTHON_VERSION` lowered from `(3, 11)` to `(3, 10)`
   - All docstrings/error messages updated to reference both #1138 and #1200
   - `test_tomllib_constraint_comment_present` broadened to also check `tomli`
   - New `test_tomli_fallback_present` regression guard added

## Key Discovery: Static Pip Install Pinning Requirement

The project has a `test_no_unpinned_static_pip_installs` test in `tests/unit/e2e/test_dockerfile.py`
(added in issue #1209) that fails if any static `RUN pip install <pkg>` line lacks an `==` pin.

Initial attempt used `tomli` (unpinned) which failed this test. Fix: use `"tomli==2.0.2"`.

## Heredoc Approach

Using `python3 - <<'PYEOF' > /tmp/deps.txt` is cleaner than `-c "try:\n import tomllib\n..."`:
- No shell quoting issues with nested quotes or `\n`
- Readable multi-line Python code
- Environment variables passed via `VAR="$VAR"` prefix

## Test Results

- 15 tests in `test_dockerfile_constraints.py` (14 original + 1 new): all pass
- 3 tests in `test_dockerfile.py` (including pinning test): all pass
- Full unit suite: 3511 passed, 0 failed
- Full suite with integration: 3585 passed, 1 skipped, 48 warnings (67.46% coverage)
- Pre-commit hooks: all passed