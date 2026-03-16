---
name: dryrun3-analysis-fix
description: "Fix 1-based subtest ID misclassification in dryrun3 analysis scripts. Use when: analysis script misreports complete/orphan/missing counts due to mixed ID numbering schemes."
category: evaluation
date: 2026-03-16
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | `analyze_dryrun3.py` misclassified active vs orphan subtests due to 1-based IDs |
| **Root Cause** | `int(sub_id) < effective_max` assumes 0-based IDs; T1-T6 use 1-based (01, 02, ...) |
| **Impact** | Script reported 0 complete tests (actual: 44), 286 missing subtests (actual: 7), 299 orphans (actual: 20) |
| **Fix** | Sort subtests by numeric ID, take first N as active (ID-scheme-agnostic) |
| **Files** | `scripts/analyze_dryrun3.py` — `classify_runs()` and `check_subtest_coverage()` |

## When to Use

- Analysis script reports 0 complete tests when runs are clearly finished
- Orphan run counts are unexpectedly high (close to total run count)
- Missing subtest counts include IDs that shouldn't exist (e.g., `00` for 1-based tiers)
- Any code that classifies subtests by numeric ID threshold with mixed numbering schemes

## Verified Workflow

### Quick Reference

The bug is in two functions in `scripts/analyze_dryrun3.py`:

**`classify_runs()`** — determines if a subtest is active or orphan:
```python
# BROKEN (assumes 0-based IDs):
sub_index = int(sub_id)
is_orphan = sub_index >= effective_max

# FIXED (ID-scheme-agnostic):
sorted_sub_ids = sorted(subtests.keys(), key=lambda s: int(s))
active_sub_ids = set(sorted_sub_ids[:effective_max])
is_orphan = sub_id not in active_sub_ids
```

**`check_subtest_coverage()`** — counts active subtests per tier:
```python
# BROKEN:
active = sum(1 for sub_id in subtests if int(sub_id) < effective_max)

# FIXED:
sorted_sub_ids = sorted(subtests.keys(), key=lambda s: int(s))
active = min(len(sorted_sub_ids), effective_max)
```

### Step-by-Step

1. **Identify the symptom**: Analysis script shows all tests incomplete, high orphan counts
2. **Trace the ID scheme**: T0 uses 0-based (00, 01, ..., 23), T1-T6 use 1-based (01, 02, ..., N)
3. **Fix `classify_runs()`**: Sort subtest keys numerically, slice first `effective_max` as active set
4. **Fix `check_subtest_coverage()`**: Same sort-and-slice pattern for counting active subtests
5. **Verify**: Run `pixi run python scripts/analyze_dryrun3.py --results-dir ~/dryrun3`

### Why Sort-and-Slice Works

For T1 with `effective_max=3` and subtests `{01, 02, 03}`:
- Old: `int("03") = 3`, `3 >= 3` = orphan (WRONG)
- New: sorted = `[01, 02, 03]`, active = `{01, 02, 03}`, all active (CORRECT)

For T0 with `effective_max=3` and subtests `{00, 01, 02}`:
- Old: `int("02") = 2`, `2 >= 3` = active (correct by accident)
- New: sorted = `[00, 01, 02]`, active = `{00, 01, 02}`, all active (CORRECT)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Original index-based approach | `int(sub_id) >= effective_max` to classify orphans | T1-T6 subtests are 1-based, so highest valid ID (e.g., 10 for T1) equals `effective_max` and gets classified as orphan | Never assume ID numbering scheme; use positional (sort-and-slice) instead of value-based comparison |
| Original coverage counting | `int(sub_id) < effective_max` to count active subtests | Same 1-based issue: counts `00` (doesn't exist) as expected, misses highest valid subtest | Same fix: count actual subtests present, capped at expected max |

## Results & Parameters

### Corrected Analysis Numbers (Post-Fix)

| Category | Old (Buggy) | Corrected |
|----------|-------------|-----------|
| Tests fully complete | 0 | 44 |
| Tests needing work | 47 | 3 |
| Complete runs (active) | 892 | 1,171 |
| Missing subtests | 286 | 7 |
| Orphan runs | 299 | 20 |

### Corrected Pass Rates (Active Runs Only)

| Tier | Pass Rate |
|------|-----------|
| T0 | 60% (119/200) |
| T1 | 54% (85/157) |
| T2 | 59% (102/172) |
| T3 | 65% (163/249) |
| T4 | 62% (105/169) |
| T5 | 67% (119/177) |
| T6 | 36% (17/47) |
| **Overall** | **60.6% (710/1171)** |

### Related Fixes in Same PR

- 7 pre-existing ruff lint issues fixed (unused vars, missing docstring, ternary simplification, line length, docstring formatting)
- Files: `scripts/analyze_dryrun3.py`, `scripts/manage_experiment.py`, `tests/unit/e2e/test_manage_experiment_run.py`
