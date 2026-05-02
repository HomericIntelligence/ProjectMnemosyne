# Raw Notes: doc-config-drift-check

## Session Details

- **Date**: 2026-02-28
- **Project**: ProjectScylla
- **Issue**: #1151 — Add CI check to prevent doc/config metric drift
- **PR**: #1225
- **Branch**: `1151-auto-impl`

## Problem Statement

During the audit for #1112, discrepancies between CLAUDE.md and pyproject.toml (coverage threshold)
and README.md (test counts, --cov path) were only caught manually. The issue requested a lightweight
CI script to automatically detect future drift.

## Implementation

### Files Created

1. `scripts/check_doc_config_consistency.py` — 236 lines
   - `load_pyproject_coverage_threshold(repo_root)` — reads `fail_under` via `tomllib`
   - `extract_cov_path_from_pyproject(repo_root)` — reads `--cov=<path>` from `addopts`
   - `check_claude_md_threshold(repo_root, expected)` — greps CLAUDE.md for `(\d+)%\+?\s+test coverage`
   - `check_readme_cov_path(repo_root, expected)` — greps README.md for `--cov=(\S+)`
   - `main()` — runs both checks, returns int (0 or 1)

2. `tests/unit/scripts/test_check_doc_config_consistency.py` — 350 lines, 26 tests
   - `TestLoadPyprojectCoverageThreshold` — 5 tests
   - `TestExtractCovPathFromPyproject` — 5 tests
   - `TestCheckClaudeMdThreshold` — 7 tests
   - `TestCheckReadmeCovPath` — 6 tests
   - `TestMainIntegration` — 3 tests

3. `.pre-commit-config.yaml` — added `check-doc-config-consistency` hook

### Actual Values in ProjectScylla

| Source | Key | Value |
| -------- | ----- | ------- |
| `pyproject.toml` | `[tool.coverage.report].fail_under` | 75 |
| `pyproject.toml` | `[tool.pytest.ini_options].addopts` | includes `--cov=scylla` |
| `CLAUDE.md` | Coverage mention | `75%+ test coverage enforced in CI` |
| `README.md` | `--cov=` usage | `--cov=scylla` |
| All pass? | Yes | Script exits 0 against real repo |

## Key Bug Encountered

**Integration test failure**: Initial `TestMainIntegration` tests used `pytest.raises(SystemExit)`
expecting `main()` to call `sys.exit()`. But `main()` returns `int` and only the `__main__` block
calls `sys.exit(main())`. Fix: changed tests to `result = main(); assert result == 0/1`.

## Pre-commit Verification

```bash
pre-commit run ruff-format-python --files scripts/check_doc_config_consistency.py tests/...
# Passed

pre-commit run ruff-check-python --files scripts/check_doc_config_consistency.py tests/...
# Passed

pre-commit run mypy-check-python --files scripts/check_doc_config_consistency.py tests/...
# Passed
```

## Test Results

- New tests: 26 passed
- Full suite: 3283 passed
- Coverage: 78.31% (above 75% threshold)
