---
name: checkpoint-result-validation
description: Validate checkpoint results before resuming expensive operations to prevent wasted API calls
category: optimization
date: 2026-01-04
tags: [checkpoint, resume, validation, cost-optimization, idempotency]
---

# Checkpoint Result Validation

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-04 |
| **Objective** | Prevent re-running expensive operations (API calls) when valid results already exist |
| **Outcome** | ✅ Added validation checks before agent/judge launches, saving costs on resume |
| **Project** | ProjectScylla |
| **PR** | [#138](https://github.com/HomericIntelligence/ProjectScylla/pull/138) |

## When to Use

Use this pattern when:
- Implementing checkpoint/resume systems
- Operations are expensive (API calls, long computations)
- Partial failures require rerunning from checkpoint
- Need idempotent resume behavior
- Want to skip already-completed work on restart

## Problem

**Naive Checkpoint Resume**:
```python
# Bad: Checks if checkpoint exists, but reruns anyway
if checkpoint.exists():
    logger.info("Resuming...")
    result = expensive_api_call()  # ❌ Wastes money if already done!
```

**Issues**:
1. Detects branch/directory exists but doesn't validate results
2. Re-runs expensive operations even if they completed successfully
3. Wastes API tokens and money
4. Slower resume times

**Evidence** (from ProjectScylla results2.log):
```
Branch T0_00 exists, attempting recovery for resume...
[AGENT] - Running agent with model[...]  # ❌ Already ran!
```

## Verified Workflow

### 1. Create Validation Functions

```python
def _has_valid_agent_result(run_dir: Path) -> bool:
    """Check if valid agent result exists.

    Returns:
        True if valid result exists with all required fields
    """
    import json

    result_file = get_agent_result_file(run_dir)
    if not result_file.exists():
        return False

    try:
        data = json.loads(result_file.read_text())
        # Validate required fields exist
        required_fields = ["exit_code", "token_stats", "cost_usd"]
        return all(field in data for field in required_fields)
    except (json.JSONDecodeError, KeyError, OSError):
        return False
```

### 2. Check BEFORE Launching

```python
# Before: Only checked file existence
if agent_result_file.exists():
    result = _load_agent_result(agent_dir)
else:
    result = expensive_agent_call()  # Runs even if partial file exists!

# After: Validate before deciding
if _has_valid_agent_result(run_dir):
    logger.info("[SKIP] Agent already completed")
    result = _load_agent_result(agent_dir)
else:
    result = expensive_agent_call()  # Only runs if needed
```

### 3. Clear Skip Logging

```python
# Use [SKIP] prefix for visibility
if _has_valid_result(run_dir):
    logger.info(f"[SKIP] Already completed: {result_file}")
    return load_result()
```

### 4. Test Resume Scenarios

```python
def test_resume_skips_completed():
    """Verify completed work is not re-run."""
    # Setup: Save valid result
    save_result(run_dir, valid_result)

    # Resume
    result = execute_with_resume(run_dir)

    # Should load, not re-run
    assert mock_api.call_count == 0
    assert result == valid_result
```

## Failed Attempts

| Approach | Why It Failed |
|----------|---------------|
| Just check file existence | Partial/corrupt files exist but are invalid |
| Validate after loading | Still pays cost of file I/O for large files |
| Trust checkpoint metadata | Metadata can be out of sync with actual results |
| No validation | Re-runs everything, defeats purpose of checkpoints |

## Results & Parameters

### Validation Pattern

```python
def _has_valid_result(result_dir: Path) -> bool:
    """Template for result validation.

    Pattern:
    1. Check file exists
    2. Try to load/parse
    3. Validate required fields
    4. Catch all exceptions
    """
    result_file = result_dir / "result.json"

    if not result_file.exists():
        return False

    try:
        data = json.loads(result_file.read_text())

        # Check required fields
        required = ["field1", "field2", "field3"]
        if not all(k in data for k in required):
            return False

        # Optional: Validate field types/values
        if not isinstance(data["field1"], int):
            return False

        return True

    except (json.JSONDecodeError, KeyError, OSError, ValueError):
        # Any error = invalid
        return False
```

### Integration with Expensive Operations

```python
def execute_with_resume(run_dir: Path):
    """Pattern for idempotent execution with validation."""

    # 1. Validate BEFORE expensive operation
    if _has_valid_result(run_dir):
        logger.info("[SKIP] Using cached result")
        return load_result(run_dir)

    # 2. Run expensive operation only if needed
    result = expensive_api_call()

    # 3. Save for future resume
    save_result(run_dir, result)

    return result
```

### Cost Savings

**Before** (from ProjectScylla logs):
- T0_00: Agent re-ran (cost: $0.15)
- T0_01: Agent re-ran (cost: $0.15)
- **Total waste: $0.30 per resume**

**After**:
- T0_00: Skipped ✅
- T0_01: Skipped ✅
- **Savings: 100% on resume**

## Key Learnings

1. **Validate Early**: Check before expensive operations, not after
2. **Required Fields**: Define minimum fields for validity
3. **Fail Safely**: Any exception = invalid, re-run
4. **Clear Logging**: `[SKIP]` prefix shows what's being skipped
5. **Test Idempotency**: Verify resume doesn't change results

## Example Use Cases

1. **ML Training**: Skip completed epochs on resume
2. **API Batch Processing**: Skip already-processed items
3. **ETL Pipelines**: Skip extracted/transformed data
4. **Experiment Runs**: Skip completed trials in ablation studies

## Related Skills

- `architecture/idempotent-operations` - Designing resumable operations
- `optimization/lazy-loading` - Defer expensive operations
- `testing/checkpoint-testing` - Testing resume scenarios

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #138 - Skip completed agent/judge runs | [notes.md](../../references/notes.md) |
