---
name: "Skill: Fix Directory Not Created Before Write"
description: "Skill: Fix Directory Not Created Before Write"
category: debugging
date: 2026-01-18
user-invocable: false
---
# Skill: Fix Directory Not Created Before Write

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-01-18 |
| **Category** | Evaluation / Debugging |
| **Objective** | Fix FileNotFoundError when writing to directory that was assigned but not created |
| **Outcome** | ✓ Success - Single line fix resolved intermittent parallel execution bug |
| **Session ID** | skill/evaluation/fix-judge-file-access |

## When to Use This Skill

Use this debugging pattern when encountering:

1. **Intermittent FileNotFoundError** in parallel execution contexts
2. **Directory path assignment without mkdir()** before file write operations
3. **Race conditions** where subdirectories sometimes create parent dirs, sometimes don't
4. **Error pattern**: `FileNotFoundError: 'path/to/parent_dir/file.json'`

### Trigger Conditions

- Error only occurs when child operations are skipped (checkpoint, early exit)
- Works when child operations run (they implicitly create parent directory)
- Parallel execution context where timing affects directory creation order

## Problem Pattern

### Vulnerable Code Pattern

```python
# VULNERABLE: Directory assigned but not created
parent_dir = base_path / "tier_name"

# ... other operations ...

# FAILS: Tries to write to parent_dir before it exists
write_file(parent_dir / "result.json", data)
```

### Root Cause

1. **Directory assignment != directory creation** in Python pathlib
2. **Implicit creation by subdirectories** masks the bug temporarily
3. **Parallel execution + checkpoints** expose the race condition

## Verified Workflow

### Step 1: Identify the Assignment Location

Search for where the problematic directory path is assigned:

```bash
grep -n "problematic_dir = " scylla/path/to/file.py
```

### Step 2: Verify No mkdir() Call

Check if `mkdir()` is called immediately after assignment:

```python
# BEFORE (bug)
tier_dir = self.experiment_dir / tier_id.value
# No mkdir() here!

# ... code continues ...

# FAILS HERE
save_selection(selection, str(tier_dir / "best_subtest.json"))
```

### Step 3: Add mkdir() Immediately After Assignment

```python
# AFTER (fixed)
tier_dir = self.experiment_dir / tier_id.value
tier_dir.mkdir(parents=True, exist_ok=True)  # ← Add this line

# Now this works reliably
save_selection(selection, str(tier_dir / "best_subtest.json"))
```

### Step 4: Verify the Fix

```bash
# Run the command that previously failed
pixi run python scripts/run_experiment.py --all-tiers --fresh

# Verify directory is created before file operations
ls -la results/experiment/tier_name/  # Should exist immediately
```

## Failed Attempts

**None** - The root cause was clear from the stack trace and the first solution worked.

### Why This Worked First Try

1. **Clear error message** pointed to exact file path
2. **Stack trace** showed `save_selection()` calling `open()` on non-existent directory
3. **Code inspection** revealed assignment without creation
4. **Pattern recognition** from pathlib behavior: assignment ≠ creation

## Key Insights

### Critical Understanding

- **Python pathlib `Path` assignment does NOT create directories**
- **Always call `.mkdir(parents=True, exist_ok=True)` after assignment**
- **Parallel execution + checkpoint resume** exposes these bugs
- **Child operations can mask parent directory bugs** by implicitly creating parents

### Best Practice Pattern

```python
# ALWAYS follow this pattern for directories that will contain files:
directory_path = parent_path / "subdir"
directory_path.mkdir(parents=True, exist_ok=True)  # Create immediately

# Now safe to write files
(directory_path / "file.json").write_text(data)
```

### Parameters That Matter

- `parents=True` - Creates parent directories if needed
- `exist_ok=True` - Doesn't error if directory already exists (idempotent)

## Results & Verification

### Fix Location

**File**: `scylla/e2e/runner.py:625`

**Change**:
```diff
  # Prepare results directory
  tier_dir = self.experiment_dir / tier_id.value
+ tier_dir.mkdir(parents=True, exist_ok=True)
```

### Verification Command

```bash
pixi run python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-002 \
  --tiers T0 T1 T2 T3 T4 T5 T6 \
  --runs 1 --max-subtests 2 -v --fresh
```

### Success Criteria

- ✓ No FileNotFoundError in any tier
- ✓ All tier directories created at start of tier execution
- ✓ T3 directory existed before save_selection() called
- ✓ Parallel execution completed without race conditions

### Commit

```
fix(e2e): create tier directory before writing best_subtest.json

Fix FileNotFoundError when save_selection() tries to write to
tier_dir/best_subtest.json before the directory exists.

Solution: Add tier_dir.mkdir(parents=True, exist_ok=True) immediately
after tier_dir assignment to ensure the directory exists before any
write operations.
```

## Reusability

This pattern applies to any code where:

1. A directory path is constructed from parent + child
2. Files are written directly to that directory (not just subdirectories)
3. There's a gap between path assignment and file write
4. The code runs in parallel or with conditional execution paths

### Common Locations

- Result directory setup in parallel executors
- Temporary workspace creation in multi-threaded code
- Checkpoint/resume systems where directory creation might be skipped
- Any path construction followed by `open(path, 'w')` or `.write_text()`

## Related Issues

- Race conditions in parallel execution
- Checkpoint resume skipping initialization steps
- Directory creation assumptions in filesystem operations
- Pathlib vs os.path behavior differences
