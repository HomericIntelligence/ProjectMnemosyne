# Raw Notes: Zero-Count Division Guard Fix

## Session: 2026-03-02, Issue #1226, PR #1315 Review

### CI Failure Traceback

Both `pre-commit` and `test (unit, tests/unit)` CI jobs crashed identically:

```
File ".../check_doc_config_consistency.py", line 309, in check_readme_test_count
    if abs(doc_count - actual_count) / actual_count > tolerance:
ZeroDivisionError: division by zero
```

### Cause Chain

1. `collect_actual_test_count()` runs `pytest --collect-only -q tests/` via subprocess
2. In CI environment, pytest reports `"0 selected"` (import errors / missing conftest)
3. Regex `r"(\d+)\s+(?:tests?\s+)?(?:selected|collected)"` matches `"0 selected"` → returns `0`
4. `main()` passes `actual_count=0` to `check_readme_test_count()`
5. Line 309: `abs(doc_count - 0) / 0` → `ZeroDivisionError`

### Fix Applied

`scripts/check_doc_config_consistency.py` lines 273-275:

```python
# Before
if m:
    return int(m.group(1))
return None

# After
if m:
    count = int(m.group(1))
    return count if count > 0 else None
return None
```

### Tests Added

`tests/unit/scripts/test_check_doc_config_consistency.py` — class `TestCollectActualTestCount`:

- `test_zero_collected_returns_none`: `"0 selected"` → `None`
- `test_zero_tests_collected_returns_none`: `"0 tests collected"` → `None`

### Verification Results

- 23/23 targeted tests pass (TestCollectActualTestCount + TestCheckReadmeTestCount + TestMainIntegration)
- 3528 total unit tests pass (1 skipped, 48 warnings — all pre-existing)
- All 20 pre-commit hooks pass including mypy, ruff, check-doc-config-consistency

### Commit

Branch: `1226-auto-impl`
Commit: `d22b17f` — "fix: Address review feedback for PR #1315"
