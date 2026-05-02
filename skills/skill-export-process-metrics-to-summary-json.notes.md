# Raw Notes: export-process-metrics (Issue #1135, 2026-02-27)

## Session Context

- **Issue:** #1135 — Add process metrics to export_data.py summary JSON output
- **Follow-up from:** #997
- **Branch:** 1135-auto-impl
- **PR:** #1182 (auto-merge enabled)
- **Duration:** Single session

## Discovery

Verified `r_prog`, `cfp`, `pr_revert_rate` exist in `build_runs_df()` at:
```
scylla/analysis/dataframes.py:147-150
```

No dataframe changes needed — pure export-layer wiring.

## Exact Line Numbers (as of PR #1182)

- `overall_stats` dict: `scripts/export_data.py` lines 706–715 (after edit: 706–721)
- `by_model` loop dict: `scripts/export_data.py` lines 744–768 (after edit: 744–779)
- `by_tier` loop dict: `scripts/export_data.py` lines 785–798 (after edit: 788–816)
- `sample_runs_df` fixture: `tests/unit/analysis/conftest.py` lines 83–108

## Pre-commit Behavior Observed

First run: ruff-format-python reformats 3 files (line length).
Second run: all hooks pass (Passed status on all).
Mypy passed on both runs without issues.

## Test Count Timeline

- Before: 3248 tests
- After: 3258 tests (+10 new tests from test_process_metrics_in_summary)

## NaN Handling Decision

Used `dropna()` + `.empty` guard rather than `isnan()` check because:
1. `np.isnan()` raises `TypeError` on non-float Series
2. `.dropna().empty` works for any dtype
3. Consistent with existing `impl_rate` handling in the same file

## json_nan_handler

Already handles `np.nan` → `null` at line ~30 of export_data.py:
```python
def json_nan_handler(obj):
    if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
        return None
    ...
```

So even if a `float(np.nan)` slipped through, it would be caught. But the `dropna().empty` guard prevents that from happening.
