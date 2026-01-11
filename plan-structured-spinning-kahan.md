# Plan: Improve LLM Judge Warning Messages

## Problem Summary

The log warnings from `llm_judge.py` are too generic and don't provide actionable information:

1. **Build pipeline warning**: `"Build pipeline: SOME FAILED"` doesn't say which steps failed
2. **Claude CLI failure**: `"Claude CLI failed (exit 1): No error message"` - stderr is empty but stdout may contain JSON error info that's being ignored

## Root Causes

### Issue 1: Generic Build Pipeline Warning
**File**: `/home/mvillmow/ProjectScylla/src/scylla/e2e/llm_judge.py:596-598`
```python
if pipeline_result.all_passed:
    logger.info("Build pipeline: ALL PASSED")
else:
    logger.warning("Build pipeline: SOME FAILED")  # No details!
```

The `BuildPipelineResult` dataclass has individual `*_passed` fields but they're not logged.

### Issue 2: Missing stdout Error Check
**File**: `/home/mvillmow/ProjectScylla/src/scylla/e2e/llm_judge.py:693-695`
```python
if result.returncode != 0:
    error_msg = result.stderr.strip() if result.stderr else "No error message"
    raise RuntimeError(f"Claude CLI failed (exit {result.returncode}): {error_msg}")
```

Claude CLI can output JSON errors to stdout (with `is_error: true`) rather than stderr, especially in `--output-format text` mode.

## Implementation Plan

### Step 1: Improve Build Pipeline Logging

Add a helper method to `BuildPipelineResult` and update the logging:

```python
# Add method to BuildPipelineResult dataclass
def get_failure_summary(self) -> str:
    """Get a summary of which pipeline steps failed."""
    failed = []
    if not self.mojo_build_passed:
        failed.append("mojo-build")
    if not self.mojo_format_passed:
        failed.append("mojo-format")
    if not self.mojo_test_passed:
        failed.append("mojo-test")
    if not self.precommit_passed:
        failed.append("pre-commit")
    return ", ".join(failed) if failed else "none"
```

Update logging at line 598:
```python
if pipeline_result.all_passed:
    logger.info("Build pipeline: ALL PASSED")
else:
    failed_steps = pipeline_result.get_failure_summary()
    logger.warning(f"Build pipeline: FAILED [{failed_steps}]")
```

### Step 2: Improve Claude CLI Error Extraction

Update `_call_claude_judge` to check stdout for JSON errors:

```python
if result.returncode != 0:
    error_msg = "No error message"

    # Check stdout for JSON error response (Claude outputs errors as JSON)
    if result.stdout:
        try:
            data = json.loads(result.stdout.strip())
            if data.get("is_error"):
                error_msg = data.get("result", data.get("error", "Unknown JSON error"))
        except json.JSONDecodeError:
            # Not JSON, check if stdout has useful text
            if result.stdout.strip():
                error_msg = f"stdout: {result.stdout.strip()[:200]}"

    # Fall back to stderr if no useful stdout
    if error_msg == "No error message" and result.stderr:
        error_msg = result.stderr.strip()

    raise RuntimeError(f"Claude CLI failed (exit {result.returncode}): {error_msg}")
```

## Files to Modify

| File | Changes |
|------|---------|
| `src/scylla/e2e/llm_judge.py:72-97` | Add `get_failure_summary()` method to `BuildPipelineResult` |
| `src/scylla/e2e/llm_judge.py:596-598` | Update build pipeline warning to include failed steps |
| `src/scylla/e2e/llm_judge.py:693-695` | Update CLI error handling to check stdout for JSON errors |

## Expected Log Output After Changes

Before:
```
WARNING: Build pipeline: SOME FAILED
WARNING: LLM judge failed, using fallback: Claude CLI failed (exit 1): No error message
```

After:
```
WARNING: Build pipeline: FAILED [mojo-build, mojo-test]
WARNING: LLM judge failed, using fallback: Claude CLI failed (exit 1): Rate limit exceeded
```

## Verification

1. Run a test experiment with a task that causes build failures
2. Verify log output shows specific failed steps (e.g., `FAILED [mojo-build, mojo-test]`)
3. Simulate a Claude CLI failure (e.g., invalid API key) and verify error message is captured from stdout JSON
4. Manual test: Run `python -c "from scylla.e2e.llm_judge import BuildPipelineResult; r = BuildPipelineResult(False, '', True, '', False, '', True, '', False); print(r.get_failure_summary())"` - should output `mojo-build, mojo-test`
