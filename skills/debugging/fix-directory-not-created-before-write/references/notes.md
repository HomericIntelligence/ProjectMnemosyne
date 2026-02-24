# Raw Session Notes: Fix Directory Not Created Before Write

## Session Context

- **Date**: 2026-01-18
- **Branch**: skill/evaluation/fix-judge-file-access
- **Issue**: FileNotFoundError: 'results/.../T3/best_subtest.json'

## Problem Description

During parallel tier execution in the e2e evaluation framework, the T3 tier would intermittently fail with:

```
FileNotFoundError: 'results/2026-01-18T21-15-01-test-002/T3/best_subtest.json'
```

## Root Cause Analysis

### Code Inspection: scylla/e2e/runner.py

**Line 624** - Directory assigned but not created:
```python
tier_dir = self.experiment_dir / tier_id.value
# No mkdir() call here!
```

**Line 661** - File write attempts before directory exists:
```python
save_selection(selection, str(tier_dir / "best_subtest.json"))
```

**Lines 702-703** - Directory created too late (in cleanup):
```python
# _save_tier_result() creates directory AFTER _run_tier() returns
tier_dir.mkdir(parents=True, exist_ok=True)
```

### Why It Was Intermittent

1. **Works when subtests execute**: Subtest creates `T3/01/run_01/` which implicitly creates parent `T3/`
2. **Fails when subtests skipped**: Checkpoint resume or early exit means no subdirectory creation
3. **Race condition**: In parallel execution, some tiers get implicit creation, others don't

## Solution

Add one line at runner.py:625:

```python
tier_dir = self.experiment_dir / tier_id.value
tier_dir.mkdir(parents=True, exist_ok=True)  # ← Added this
```

## Verification Process

### Step 1: Code Verification
```bash
# Confirmed mkdir is now called immediately after assignment
grep -A 1 "tier_dir = self.experiment_dir / tier_id.value" scylla/e2e/runner.py
```

### Step 2: Live Test
```bash
pixi run python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-002 \
  --tiers T0 T1 T2 T3 T4 T5 T6 \
  --runs 1 --max-subtests 2 -v --fresh
```

**Results**:
- T3 directory created at 13:15:07 (start of tier execution)
- T3 subtests (01, 02) both completed successfully
- No FileNotFoundError occurred
- Directory structure verified:
  ```
  results/2026-01-18T21-15-01-test-002/T3/
  ├── 01/
  │   └── run_01/
  └── 02/
      └── run_01/
  ```

### Step 3: Error Log Check
```bash
grep -i "filenotfounderror\|no such file" output.log
# Result: No matches - fix confirmed working
```

## Commit Details

**Commit**: beb8ed7
**Message**:
```
fix(e2e): create tier directory before writing best_subtest.json

Fix FileNotFoundError when save_selection() tries to write to
tier_dir/best_subtest.json before the directory exists.

The bug occurred in parallel tier execution when all subtests were
skipped or loaded from checkpoint. The tier directory was assigned
at line 624 but never created, causing save_selection() at line 661
to fail.

Solution: Add tier_dir.mkdir(parents=True, exist_ok=True) immediately
after tier_dir assignment to ensure the directory exists before any
write operations.

Fixes: results/.../T3/best_subtest.json FileNotFoundError

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Pre-commit Hooks**: All passed
- ruff: Passed
- ruff-format: Passed

**Status**: Pushed to remote

## Key Learnings

1. **Python pathlib quirk**: `Path()` assignment does NOT create directories
2. **Always call mkdir() immediately** after path assignment if files will be written
3. **Parallel + checkpoint = race condition exposer** - great for finding these bugs
4. **Child operations can mask parent bugs** - subdirectory creation implicitly creates parents

## Pattern Recognition

This bug pattern appears when:
- Directory path assigned: `dir = parent / "name"`
- No mkdir() call: Missing `dir.mkdir(...)`
- File write later: `(dir / "file").write_text(...)`
- Conditional execution: Sometimes subdirs create parent, sometimes not

## Prevention

Add to code review checklist:
- [ ] Every directory path assignment followed by mkdir()?
- [ ] All file write operations verify parent directory exists?
- [ ] Parallel execution paths tested without child directory creation?
