---
name: debug-evaluation-logs
description: Improving diagnostic clarity of LLM judge warning messages by adding specific failure details
category: evaluation
date: 2026-01-08
---

# Skill: Debug Evaluation Logs

## Overview

| Property | Value |
|----------|-------|
| **Date** | 2026-01-08 |
| **Category** | Evaluation |
| **Objective** | Improve diagnostic clarity of LLM judge warning messages |
| **Outcome** | ✅ Success - Two targeted improvements to llm_judge.py |
| **Files Modified** | `src/scylla/e2e/llm_judge.py` |
| **Context** | ProjectScylla evaluation infrastructure |

When analyzing evaluation experiment logs, generic warning messages made it difficult to diagnose failures. Log output like "Build pipeline: SOME FAILED" and "Claude CLI failed (exit 1): No error message" provided no actionable information about what actually went wrong.

## When to Use

Apply this pattern when:

1. **Ambiguous failure logs**: Warning messages don't specify what failed
2. **Missing error context**: Error handlers discard useful diagnostic information
3. **Composite operations**: Multi-step pipelines don't report which steps failed
4. **JSON error responses**: Subprocess errors output structured data to stdout instead of stderr

**Trigger phrases**:
- "The logs don't show what failed"
- "Warning messages are too generic"
- "Error says 'No error message'"
- "Can't tell which pipeline step failed"

## Problem Analysis

### Issue 1: Generic Build Pipeline Warning

**Location**: `src/scylla/e2e/llm_judge.py:596-598`

**Symptoms**:
```
[WARNING] Build pipeline: SOME FAILED
```

No indication which of the 4 pipeline steps (mojo-build, mojo-format, mojo-test, pre-commit) failed.

**Root Cause**:
The `BuildPipelineResult` dataclass tracked individual step results but didn't expose a summary method for logging.

### Issue 2: Missing Claude CLI Error Messages

**Location**: `src/scylla/e2e/llm_judge.py:693-695`

**Symptoms**:
```
[WARNING] LLM judge failed, using fallback: Claude CLI failed (exit 1): No error message
```

**Root Cause**:
Claude CLI outputs JSON error responses to stdout (especially with `--output-format text`), not stderr. The error handler only checked stderr, so JSON errors like rate limits were lost.

## Verified Workflow

### Step 1: Add Diagnostic Summary Method

Add a method to composite result objects that summarizes failures:

```python
@dataclass
class BuildPipelineResult:
    mojo_build_passed: bool
    mojo_format_passed: bool
    mojo_test_passed: bool
    precommit_passed: bool
    all_passed: bool
    # ... outputs ...

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

**Why this works**:
- Returns actionable list of failed components
- Returns "none" when all pass (clear negative signal)
- Comma-separated format is grep-friendly

### Step 2: Use Summary in Warning Messages

```python
if pipeline_result.all_passed:
    logger.info("Build pipeline: ALL PASSED")
else:
    failed_steps = pipeline_result.get_failure_summary()
    logger.warning(f"Build pipeline: FAILED [{failed_steps}]")
```

**Before**: `WARNING: Build pipeline: SOME FAILED`
**After**: `WARNING: Build pipeline: FAILED [mojo-build, mojo-test]`

### Step 3: Check Multiple Error Sources in Priority Order

For subprocesses that may output errors to different streams:

```python
if result.returncode != 0:
    error_msg = "No error message"

    # Priority 1: Check stdout for JSON error response
    if result.stdout:
        try:
            data = json.loads(result.stdout.strip())
            if data.get("is_error"):
                error_msg = data.get("result", data.get("error", "Unknown JSON error"))
        except json.JSONDecodeError:
            # Priority 2: Use plain stdout if not JSON
            if result.stdout.strip():
                error_msg = f"stdout: {result.stdout.strip()[:200]}"

    # Priority 3: Fall back to stderr
    if error_msg == "No error message" and result.stderr:
        error_msg = result.stderr.strip()

    raise RuntimeError(f"Claude CLI failed (exit {result.returncode}): {error_msg}")
```

**Key Pattern**: Try to extract structured errors first, then fall back to plain text, checking both stdout and stderr.

## Failed Attempts

| Approach | Why It Failed | Lesson Learned |
|----------|---------------|----------------|
| None | Initial approach worked | Proper exploration phase identified exact problem locations and solutions |

**Note**: This skill had no failed attempts because the diagnostic phase clearly identified both issues (generic warnings and missing error messages) before implementation began.

## Results

### Build Pipeline Warning Output

**Test Case**: Two pipeline steps fail (mojo-build, mojo-test)

```bash
pixi run python -c "from scylla.e2e.llm_judge import BuildPipelineResult; \
  r = BuildPipelineResult(False, '', True, '', False, '', True, '', False); \
  print(r.get_failure_summary())"
```

**Output**: `mojo-build, mojo-test`

### Log Output Improvement

**Before**:
```
2026-01-08 15:54:16 [WARNING] Build pipeline: SOME FAILED
2026-01-08 15:54:20 [WARNING] LLM judge failed, using fallback: Claude CLI failed (exit 1): No error message
```

**After**:
```
2026-01-08 15:54:16 [WARNING] Build pipeline: FAILED [mojo-build, mojo-test]
2026-01-08 15:54:20 [WARNING] LLM judge failed, using fallback: Claude CLI failed (exit 1): Rate limit exceeded
```

## Key Learnings

### 1. Composite Result Patterns

When returning results from multi-step operations, always provide:
- Individual step results (for programmatic access)
- Summary method (for human-readable diagnostics)

```python
@dataclass
class MultiStepResult:
    step1_passed: bool
    step2_passed: bool
    all_passed: bool

    def get_failure_summary(self) -> str:
        """Always provide this for logging."""
        failed = []
        if not self.step1_passed:
            failed.append("step1")
        if not self.step2_passed:
            failed.append("step2")
        return ", ".join(failed) if failed else "none"
```

### 2. Subprocess Error Extraction Priority

For modern CLIs that use `--output-format` flags:

1. **Check stdout for JSON**: Many CLIs output structured errors to stdout
2. **Check stdout for plain text**: May contain useful diagnostic output
3. **Check stderr**: Traditional error stream
4. **Default**: "No error message" (but try the above first)

### 3. Warning Message Format

**Poor**: `"Operation failed"` (no context)
**Better**: `"Build failed"` (what failed)
**Best**: `"Build failed [syntax-check, lint]"` (what failed + details)

Use brackets `[]` for machine-parseable details within human messages.

## Testing

### Manual Testing

```bash
# Test get_failure_summary
pixi run python -c "from scylla.e2e.llm_judge import BuildPipelineResult; \
  r = BuildPipelineResult(False, '', True, '', False, '', True, '', False); \
  print('Failed:', r.get_failure_summary())"
# Output: Failed: mojo-build, mojo-test

# Syntax check
python -m py_compile src/scylla/e2e/llm_judge.py
# Output: ✓ Syntax check passed
```

### Integration Testing

Run an evaluation experiment with tasks that trigger build failures and verify log output shows specific failed steps.

## Reusable Patterns

### Pattern 1: Diagnostic Summary for Composite Results

**When to use**: Any dataclass that represents multiple boolean outcomes

```python
@dataclass
class ValidationResult:
    syntax_valid: bool
    type_valid: bool
    lint_valid: bool
    all_valid: bool

    def get_failure_summary(self) -> str:
        """Get comma-separated list of failed validations."""
        failed = []
        if not self.syntax_valid:
            failed.append("syntax")
        if not self.type_valid:
            failed.append("types")
        if not self.lint_valid:
            failed.append("lint")
        return ", ".join(failed) if failed else "none"
```

**Usage in logging**:
```python
if not result.all_valid:
    logger.warning(f"Validation failed: [{result.get_failure_summary()}]")
```

### Pattern 2: Multi-Source Error Extraction

**When to use**: Handling subprocess errors that may appear in multiple streams

```python
def extract_subprocess_error(result: subprocess.CompletedProcess) -> str:
    """Extract error message from subprocess result, checking multiple sources."""
    error_msg = "No error message"

    # Priority 1: Check stdout for JSON errors
    if result.stdout:
        try:
            data = json.loads(result.stdout.strip())
            if data.get("is_error"):
                return data.get("result", data.get("error", "Unknown JSON error"))
        except json.JSONDecodeError:
            pass

    # Priority 2: Plain stdout
    if result.stdout and result.stdout.strip():
        error_msg = f"stdout: {result.stdout.strip()[:200]}"

    # Priority 3: stderr
    if error_msg == "No error message" and result.stderr:
        error_msg = result.stderr.strip()

    return error_msg
```

## References

- **Original log analysis**: User provided experiment logs showing generic warnings
- **Modified file**: `ProjectScylla/src/scylla/e2e/llm_judge.py`
- **Related work**: Multi-judge consensus support (parallel work on same file)
- **ProjectScylla commit**: skill/evaluation/multi-judge-consensus branch

## Related Skills

- **error-message-improvement**: General error message enhancement patterns
- **structured-logging**: Using consistent formats for machine parsing
- **diagnostic-methods**: Adding `get_*_summary()` methods to complex types
- **subprocess-error-handling**: Robust error extraction from subprocess calls

## Tags

`#evaluation` `#logging` `#diagnostics` `#error-handling` `#llm-judge` `#pipeline` `#subprocess`
