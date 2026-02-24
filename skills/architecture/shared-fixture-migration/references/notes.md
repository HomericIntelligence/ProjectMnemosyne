# Session Notes: shared-fixture-migration

## Date: 2026-01-03

## Problem Statement

Test fixtures in ProjectScylla contained massive duplication:
- 5,361 config.yaml files across 47 tests
- 5,355 (99.9%) were duplicates
- 119 unique subtest configurations repeated 47 times each
- Total fixture size: 47MB

## Solution Summary

Created a centralized shared subtests directory with runtime loading:
1. Moved 119 unique configs to `tests/claude-code/shared/subtests/t{0-6}/`
2. Modified `tier_manager.py` to load from shared first, overlay test-specific
3. Deleted all per-test tier directories

## Results

| Metric | Before | After |
|--------|--------|-------|
| Fixture size | 47MB | 1.4MB |
| config.yaml files | 5,361 | 160 |
| Lines deleted | - | 120,735 |

## Key Files Modified

- `src/scylla/e2e/tier_manager.py` - Added shared subtests loading
- `scripts/migrate_subtests_to_shared.py` - Migration script
- `scripts/validate_tier_manager.py` - Validation script

## Validation Output

```
============================================================
Validating TierManager with centralized shared subtests
============================================================

--- Shared Subtests Directory ---
  T0: 24 subtests
  T1: 10 subtests
  T2: 15 subtests
  T3: 41 subtests
  T4: 7 subtests
  T5: 15 subtests
  T6: 1 subtests
  Total: 113 shared subtest configs

--- Loading Tiers via TierManager ---
  T0: 24 subtests (expected 24) [PASS]
  T1: 10 subtests (expected 10) [PASS]
  T2: 15 subtests (expected 15) [PASS]
  T3: 41 subtests (expected 41) [PASS]
  T4: 7 subtests (expected 7) [PASS]
  T5: 15 subtests (expected 15) [PASS]
  T6: 1 subtests (expected 1) [PASS]

============================================================
VALIDATION PASSED - TierManager loads from shared correctly
============================================================
```

## Key Learnings

1. **Always run hash analysis first** - Use `find | md5sum | uniq -c` to identify actual duplication source
2. **Check ALL file types** - Initial T0 migration left T1-T6 untouched
3. **Distinguish test-specific vs shared** - Only prompts, expected results need to be per-test
