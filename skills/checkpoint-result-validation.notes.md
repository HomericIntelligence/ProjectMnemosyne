# Checkpoint Result Validation - Implementation Notes

## Context

ProjectScylla E2E experiments were re-running expensive agent/judge calls on resume even when results already existed:

```
# results2.log:14-16
Branch T0_00 exists, attempting recovery for resume...
[AGENT] - Running agent with model[...]  # Should have been skipped!
```

This wasted API tokens ($0.15 per agent run) and time.

## Root Cause

Code only checked if result file EXISTS, not if it's VALID:

```python
# Before (subtest_executor.py:571):
if agent_result_file.exists():
    result = _load_agent_result(agent_dir)
else:
    result = run_agent()  # Runs even if partial/corrupt file exists
```

## Solution

Added validation functions:

```python
def _has_valid_agent_result(run_dir: Path) -> bool:
    result_file = get_agent_result_file(run_dir)
    if not result_file.exists():
        return False

    try:
        data = json.loads(result_file.read_text())
        required_fields = ["exit_code", "token_stats", "cost_usd"]
        return all(field in data for field in required_fields)
    except (json.JSONDecodeError, KeyError, OSError):
        return False
```

Updated execution logic:

```python
# After:
if _has_valid_agent_result(run_dir):
    logger.info("[SKIP] Agent already completed")
    result = _load_agent_result(agent_dir)
else:
    result = run_agent()  # Only if needed
```

## Files Changed

- `src/scylla/e2e/subtest_executor.py`:
  - Added `_has_valid_agent_result()` function (23 lines)
  - Added `_has_valid_judge_result()` function (23 lines)
  - Updated agent execution check (line 611)
  - Updated judge execution check (line 688)

## Benefits

1. **Cost Savings**: No duplicate API calls on resume
2. **Faster Resume**: Only runs incomplete work
3. **Integrity**: Validates required fields present
4. **Clear Logs**: `[SKIP]` shows what's being skipped

## Testing

Manually tested resume scenarios:
- Resume after crash during agent → Skips completed agents ✅
- Resume with corrupt result file → Re-runs agent ✅
- Resume with missing field → Re-runs agent ✅

## PR Details

- **Branch**: `132-skip-completed-runs`
- **Files Changed**: 1 modified
- **Lines**: +60, -11
- **Dependencies**: PR #137 (paths module)
- **Status**: Awaiting merge
