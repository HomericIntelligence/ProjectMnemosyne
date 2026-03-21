# Dryrun3 Analysis Fix — Session Notes

## Date: 2026-03-16

## Context

PR #1502 (always-retry infra failures in `resume_manager.py`) was already merged.
This session focused on the analysis script bug discovered during live dryrun3 analysis.

## Bug Details

### Root Cause

`scripts/analyze_dryrun3.py` has two functions that classify subtests as active vs orphan:

1. `classify_runs()` (line 94-95): `is_orphan = int(sub_id) >= effective_max`
2. `check_subtest_coverage()` (line 131): `active = sum(1 for sub_id in subtests if int(sub_id) < effective_max)`

Both assume 0-based subtest IDs. T0 is 0-based (00, 01, ..., 23) but T1-T6 are 1-based (01, 02, ..., N).

### Example: T1 with max_subtests=10

- Subtests: `{01, 02, 03, 04, 05, 06, 07, 08, 09, 10}`
- `effective_max = min(10, 10) = 10`
- Old code: `int("10") = 10`, `10 >= 10` → orphan (WRONG — subtest 10 is valid)
- Old code also expected `int("00") = 0`, `0 < 10` → counted, but `00` doesn't exist → reported as missing

### Fix Pattern

Sort subtest keys by numeric value, take first `effective_max` as the active set:

```python
sorted_sub_ids = sorted(subtests.keys(), key=lambda s: int(s))
active_sub_ids = set(sorted_sub_ids[:effective_max])
```

This works regardless of whether IDs start at 0 or 1.

## Ruff Lint Fixes (Pre-existing)

7 ruff issues fixed across 3 files:
- `RUF059`: Unused unpacked variables `state` and `reasons` → prefixed with `_`
- `SIM108`: If-else block → ternary for `expected_runs`
- `B007`: Unused loop variable `tier_id` → `_tier_id`
- `D103`: Missing docstring for `main()`
- `D205`: Docstring summary/description blank line in `manage_experiment.py`
- `E501`: Line too long in test file → wrapped comment

## Commit

```
fix(dryrun3): fix 1-based subtest ID bug in analyze_dryrun3.py and resolve ruff lint issues
```

Branch: `1490-always-retry-infra-failures`
All 4873 tests passed, 77.19% coverage.