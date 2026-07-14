---
name: logging-subprocess-context-tracking
description: "Add diagnostic context (working directory, command, cwd) to subprocess execution logging. Use when: (1) run_git_cmd or similar subprocess runners log execution without showing which directory the command ran in, (2) debugging multi-directory workflows where cwd context is critical for tracing, (3) writing tests for subprocess execution and caplog fixture fails with custom logger handlers (propagate=False)."
category: debugging
date: 2026-06-05
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - logging
  - subprocess
  - working-directory
  - pytest
  - caplog
  - custom-handlers
  - context-tracking
---

# Logging Subprocess Execution with Working Directory Context

## Overview

| Field | Value |
|-------|-------|
| **Objective** | Add working directory and other diagnostic context to subprocess execution logs; understand when pytest caplog fixture fails with custom logger setup |
| **Scope** | Conditional logging for subprocess calls; pytest logging mocking patterns for custom handler setup |
| **Root Problem** | When subprocess runners execute in different working directories, the log output contains no cwd context, making multi-directory workflows difficult to debug. Additionally, pytest caplog fixture does not work with loggers configured with `propagate=False` and custom handlers. |
| **Verification** | verified-ci (all 48 tests pass, PR #960 merged in ProjectHephaestus) |

## When to Use

- Logging subprocess execution (git commands, shell scripts) and the log lines don't show which directory the command ran in
- Debugging multi-step workflows where commands run in different working directories and trace logs are ambiguous
- Writing unit tests for subprocess runners and caplog fixture silently captures nothing (logger has `propagate=False` or custom handlers)
- Needing to add diagnostic context to existing subprocess helpers without major refactoring

## Verified Workflow

### Quick Reference

**Problem**: `logger.info("Running git command")` omits the working directory context.

**Solution**: Conditional format string — when `cwd` is not None, append `(cwd=path)` suffix; when cwd is None, preserve existing log format for backward compatibility.

```python
# In subprocess runner function
def run_git_cmd(cmd: list[str], cwd: str | None = None) -> str:
    """Run git command in optional working directory."""

    # Conditional log formatting
    if cwd is not None:
        logger.info(f"Running: {' '.join(cmd)} (cwd={cwd})")
    else:
        logger.info(f"Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.stdout
```

### Detailed Steps

#### Step 1: Identify the subprocess runner function

Locate the function that invokes subprocess calls. Examples:
- `run_git_cmd()` in ProjectHephaestus `hephaestus/github/pr_merge.py:60-80`
- Custom shell execution wrappers
- DevOps automation scripts that orchestrate multi-directory workflows

#### Step 2: Add optional `cwd` parameter (if not present)

```python
def run_git_cmd(cmd: list[str], cwd: str | None = None) -> str:
    """Run git command in optional working directory.

    Args:
        cmd: Command and arguments as list of strings
        cwd: Working directory for command execution (None = current directory)

    Returns:
        stdout from the command
    """
```

#### Step 3: Implement conditional logging

When cwd is provided, log includes the directory context. When cwd is None (default), log is unchanged to avoid noisy output.

```python
def run_git_cmd(cmd: list[str], cwd: str | None = None) -> str:
    # Conditional format — include cwd only when not None
    if cwd is not None:
        logger.info(f"Running git command: {' '.join(cmd)} (cwd={cwd})")
    else:
        logger.info(f"Running git command: {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
    return result.stdout
```

#### Step 4: Write unit tests using logger mocking (NOT caplog)

**CRITICAL**: pytest caplog fixture does NOT work with loggers configured with `propagate=False` and custom handlers. Use unittest.mock to patch the logger directly.

```python
from unittest.mock import patch, MagicMock
import logging

def test_run_git_cmd_with_cwd_logs_context():
    """Test that cwd context is logged when provided."""
    with patch("hephaestus.github.pr_merge.logger") as mock_logger:
        run_git_cmd(["git", "status"], cwd="/tmp/test_repo")

        # Verify the logger call includes the cwd context
        call_args = mock_logger.info.call_args
        assert call_args is not None
        logged_message = call_args[0][0]  # First positional arg of the format string
        assert "(cwd=/tmp/test_repo)" in logged_message

def test_run_git_cmd_without_cwd_no_context():
    """Test that cwd is omitted from log when not provided."""
    with patch("hephaestus.github.pr_merge.logger") as mock_logger:
        run_git_cmd(["git", "status"])

        # Verify the logger call does NOT include cwd context
        call_args = mock_logger.info.call_args
        assert call_args is not None
        logged_message = call_args[0][0]
        assert "(cwd=" not in logged_message
```

**Key differences from caplog approach**:
- Use `@patch("module.logger")` to mock the logger directly
- Inspect `mock_logger.info.call_args` to verify logged content
- Works reliably with `propagate=False` and custom handlers
- More explicit about what is being tested (the log call itself, not the output)

### Why caplog fails with custom handlers

The pytest caplog fixture captures output by attaching a handler to the root logger and checking output. However:

1. If logger has `propagate=False`, records do not propagate to the root logger
2. caplog's handler never sees the record
3. Test assertion `assert "text" in caplog.text` returns False even though the message was logged

This is NOT a bug in the logger code — it's a test infrastructure mismatch. The fix is to test through mocking, which validates the logger call without depending on propagation.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using pytest caplog fixture | `caplog.records` and `caplog.text` to verify logged output | caplog only captures from the root logger; custom handler with `propagate=False` never sends records there | Mock the logger directly with `@patch`; test the call, not the output |
| Static f-string in log statement | `logger.info(f"Running: {cmd} (cwd={cwd})")` unconditionally | When cwd is None (the common case), output is noisy with `(cwd=None)` suffix | Use conditional — only append context when cwd is not None |
| Logging cwd as separate call | `logger.info(f"Running: {cmd}"); if cwd: logger.info(f"cwd={cwd}")` | Two separate log lines are harder to correlate when reading logs; adds verbosity | Single conditional log line with context appended when relevant |
| Using f-string only (no logger.info) | `print(f"Running: {cmd} (cwd={cwd})")` | print output goes to stdout, not the logging system; not captured by loggers or structured logs | Always use logger.info() for subprocess execution traces |
| Attempting to use caplog with mock patch | `mock_logger.info.call_args` AND `caplog.text` together | caplog and mock patch interfere; patch replaces the logger before caplog can attach its handler | Choose one: either mock the logger directly (simpler) or use caplog (requires propagate=True) |
| Adding cwd to logger context via contextvars | `logging.contextvars.bind(cwd=...)` | Some logging systems support this; Python's standard logging does not have built-in contextvars integration without additional libraries | Use simple conditional f-string; avoid adding dependencies |
| Making cwd a format field via LoggerAdapter | `LoggerAdapter(logger, {"cwd": cwd})` | Works only if every call site creates the adapter; requires refactoring call sites | Simple conditional log format is more localized and easier to review |

## Results & Parameters

### Log output examples

```
# Before (no cwd context):
2026-06-05 10:12:34 [INFO] hephaestus.github.pr_merge: Running git command: ['git', 'status']

# After (with cwd context):
2026-06-05 10:12:34 [INFO] hephaestus.github.pr_merge: Running git command: ['git', 'status'] (cwd=/tmp/test_repo)
```

### Test mocking pattern (pytest)

```python
from unittest.mock import patch

def test_subprocess_runner_with_cwd():
    """Test that working directory context is logged."""
    with patch("module_name.logger") as mock_logger:
        result = run_git_cmd(["git", "log", "--oneline"], cwd="/home/user/repo")

        # Verify logger.info was called
        assert mock_logger.info.called

        # Extract the logged message (first positional argument)
        logged_msg = mock_logger.info.call_args[0][0]

        # Assertions on the message content
        assert "git log --oneline" in logged_msg or isinstance(logged_msg, str)
        assert "(cwd=/home/user/repo)" in logged_msg
```

### Code change example (ProjectHephaestus PR #960)

**File**: `hephaestus/github/pr_merge.py` lines 74-76

**Before**:
```python
logger.info(f"Running git command: {' '.join(cmd)}")
```

**After**:
```python
if cwd is not None:
    logger.info(f"Running git command: {' '.join(cmd)} (cwd={cwd})")
else:
    logger.info(f"Running git command: {' '.join(cmd)}")
```

### Test setup checklist

- [ ] Function has optional `cwd: str | None = None` parameter
- [ ] Conditional logging appends `(cwd=path)` only when cwd is not None
- [ ] Tests use `@patch("module.logger")` to mock the logger
- [ ] Test extracts message from `mock_logger.info.call_args[0][0]`
- [ ] Test asserts the cwd context is present (or absent) as expected
- [ ] No caplog fixture used in subprocess logging tests
- [ ] All tests pass locally and in CI

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #771 — PR #960 | Add cwd context to run_git_cmd logging; 48 tests pass, all CI checks green |
| ProjectHephaestus | Unit test suite | `tests/unit/github/test_pr_merge.py` — 2 new test cases using logger mock patches |
