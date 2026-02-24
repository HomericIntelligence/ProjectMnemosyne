# Raw Session Notes — Move Loose Test Files

## Session Context

- **Date**: 2026-02-22
- **Issue**: HomericIntelligence/ProjectScylla#849
- **Branch**: `849-auto-impl`
- **PR**: HomericIntelligence/ProjectScylla#964

## Files Moved

```
tests/unit/test_config_loader.py     → tests/unit/config/test_config_loader.py
tests/unit/test_docker.py            → tests/unit/executor/test_docker.py
tests/unit/test_grading_consistency.py → tests/unit/metrics/test_grading_consistency.py
```

## Key Decision: Naming Conflict Avoidance

Issue proposed destination `tests/unit/config/test_loader.py` but `test_loader.py` already existed
in that directory. Reading both files revealed:

- **Existing `test_loader.py`**: Tests production model config validation (filename/model_id
  consistency, `load_all_models()` with real configs)
- **Incoming `test_config_loader.py`**: Tests `ConfigLoader` with fixture data (defaults, eval
  cases, rubrics, tiers, merged config, edge cases)

Decision: Keep name `test_config_loader.py` to avoid clobbering. Both files test different aspects.

## Fixture Path Bug Details

**File**: `tests/unit/test_config_loader.py` line 32

```python
FIXTURES_PATH = Path(__file__).parent.parent / "fixtures"
```

Old location resolution:
- `Path(__file__)` = `tests/unit/test_config_loader.py`
- `.parent` = `tests/unit/`
- `.parent` = `tests/`
- `/ "fixtures"` = `tests/fixtures/` ✓ (correct)

New location resolution (before fix):
- `Path(__file__)` = `tests/unit/config/test_config_loader.py`
- `.parent` = `tests/unit/config/`
- `.parent` = `tests/unit/`
- `/ "fixtures"` = `tests/unit/fixtures/` ✗ (directory doesn't exist!)

Fixed to:
```python
FIXTURES_PATH = Path(__file__).parent.parent.parent / "fixtures"
```

New location resolution (after fix):
- `.parent` = `tests/unit/config/`
- `.parent.parent` = `tests/unit/`
- `.parent.parent.parent` = `tests/`
- `/ "fixtures"` = `tests/fixtures/` ✓

## Failure Symptom (Before Fix)

```
FAILED tests/unit/config/test_config_loader.py::TestConfigLoaderEvalCase::test_load_test
  scylla.config.models.ConfigurationError: Configuration file not found:
  /home/mvillmow/ProjectScylla/.worktrees/issue-849/tests/unit/fixtures/tests/test-001/test.yaml
```

18 tests failed across: TestConfigLoaderEvalCase, TestConfigLoaderRubric,
TestConfigLoaderTier, TestConfigLoaderMerged (all fixture-dependent tests).

Tests using `tmp_path` or `tempfile.TemporaryDirectory` were unaffected (17 passed).

## CI Verification

`.github/workflows/test.yml` uses `tests/unit` as a directory argument — no file-level hardcoding.
No changes to CI config were needed.

## Pre-commit Results

All 15 hooks passed:
- Ruff Format, Ruff Check, Mypy Type Check ✓
- Check Mypy Known Issue Counts ✓
- Validate Model Config Naming (skipped — no config files changed) ✓
- Markdown Lint, YAML Lint, ShellCheck ✓
- Trim Trailing Whitespace, Fix End of Files, etc. ✓

## Test Count Verification

| Phase | Count |
|-------|-------|
| Baseline (before moves) | 2432 passed, 8 warnings |
| After config move + path fix | 157 config tests pass |
| After executor move | 169 executor tests pass |
| After metrics move | 241 metrics tests pass |
| Full suite final | 2432 passed, 8 warnings ✓ |

Coverage: 74.16% (above 73% threshold, unchanged).
