---
name: subprocess-expected-failure-log-suppress
description: "Suppress logger.error() for expected CalledProcessError in run_subprocess() and git_utils.run() using log_on_error/log_errors=False. Use when: (1) a subprocess call probes for an optional resource (git ref, remote branch) and failure is expected, (2) a first-try cleanup attempt is expected to fail on clean state, (3) callers catch and handle CalledProcessError themselves so ERROR log entries are noise."
category: tooling
date: 2026-04-22
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - subprocess
  - logging
  - run_subprocess
  - log_on_error
  - log_errors
  - CalledProcessError
  - expected-failure
  - git-utils
  - hephaestus
---

# Suppress Logs for Expected Subprocess Failures

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-22 |
| **Objective** | Suppress noisy ERROR log entries for subprocess failures that callers intentionally catch and handle |
| **Outcome** | Success — 1403 tests pass, PR #301 merged |
| **Verification** | verified-ci |
| **Project** | ProjectHephaestus, PR #301 (branch: port-circuit-breaker-success-threshold) |

## When to Use

- A `run_subprocess()` call probes for an optional resource (e.g., `git rev-parse --verify <ref>`) where absence is a valid expected outcome
- A first-try cleanup attempt (e.g., `git worktree remove <path>`) is designed to fail if the path does not exist yet
- The caller already catches `CalledProcessError` and recovers gracefully — so the `logger.error()` inside the helper is pure noise in logs
- You see ERROR log spam from expected subprocess failures during normal operation

**Keyword triggers**: `log_on_error`, `log_errors`, subprocess, git probe, expected failure, suppress error log

## Verified Workflow

### Quick Reference

```python
# For run_subprocess() in hephaestus/utils/helpers.py
result = run_subprocess(
    ["git", "rev-parse", "--verify", branch_name],
    check=False,         # Don't raise — check returncode yourself
    log_on_error=False,  # Suppress ERROR log if it fails
)

# For git_utils.run() in hephaestus/automation/git_utils.py
result = run(
    ["git", "worktree", "remove", path],
    check=False,
    log_errors=False,    # Suppress ERROR log for expected removal failures
)
```

### Detailed Steps

1. **Identify the noisy call site**: Look for `run_subprocess()` or `git_utils.run()` calls where:
   - The exception is immediately caught by the caller
   - OR `check=False` is used and the caller inspects `returncode` directly
   - AND the failure is expected in normal operation

2. **Add `log_on_error=False` to `run_subprocess()` calls**:

   ```python
   # BEFORE (noisy)
   result = run_subprocess(
       ["git", "rev-parse", "--verify", branch_name],
       check=False,
   )
   branch_exists = result.returncode == 0

   # AFTER (clean logs)
   result = run_subprocess(
       ["git", "rev-parse", "--verify", branch_name],
       check=False,
       log_on_error=False,
   )
   branch_exists = result.returncode == 0
   ```

3. **Add `log_errors=False` to `git_utils.run()` calls**:

   ```python
   # BEFORE (noisy)
   try:
       run(["git", "worktree", "remove", str(path)])
   except CalledProcessError:
       pass  # Expected if not yet created

   # AFTER (clean logs)
   try:
       run(["git", "worktree", "remove", str(path)], log_errors=False)
   except CalledProcessError:
       pass  # Expected if not yet created
   ```

4. **Verify the exception still propagates**: The `log_on_error=False` / `log_errors=False` flag ONLY suppresses the `logger.error()` call. The `CalledProcessError` still propagates normally so callers that do NOT catch it will still fail loudly.

5. **Implementation reference** — signature changes made in PR #301:

   ```python
   # hephaestus/utils/helpers.py
   def run_subprocess(
       cmd: list[str],
       *,
       check: bool = True,
       log_on_error: bool = True,   # ← new kwarg
       **kwargs,
   ) -> subprocess.CompletedProcess:
       try:
           return subprocess.run(cmd, check=check, **kwargs)
       except subprocess.CalledProcessError as e:
           if log_on_error:
               logger.error(f"Command failed: {e.cmd!r} → exit {e.returncode}")
           raise

   # hephaestus/automation/git_utils.py
   def run(
       cmd: list[str | Path],
       *,
       check: bool = True,
       log_errors: bool = True,     # ← new kwarg
       **kwargs,
   ) -> subprocess.CompletedProcess:
       try:
           return subprocess.run([str(c) for c in cmd], check=check, **kwargs)
       except subprocess.CalledProcessError as e:
           if log_errors:
               logger.error(f"git command failed: {e.cmd!r} → exit {e.returncode}")
           raise
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A — direct approach | The pattern was clear from the first probe site in worktree_manager.py | N/A | Callers that catch CalledProcessError are the canonical signal that the failure is expected |

## Results & Parameters

### Files Changed

| File | Change |
|------|--------|
| `hephaestus/utils/helpers.py` | Added `log_on_error: bool = True` kwarg; guard `logger.error()` with it |
| `hephaestus/automation/git_utils.py` | Added `log_errors: bool = True` kwarg; guard `logger.error()` with it |
| `hephaestus/automation/worktree_manager.py` | Pass `log_errors=False` at probe/cleanup call sites |

### Default behavior preserved

Both kwargs default to `True` — existing callers that did NOT pass the flag continue to log errors exactly as before. Only explicitly opted-in call sites suppress logs.

### Canonical use cases in hephaestus/automation/worktree_manager.py

```python
# 1. Probe: does branch exist?
result = run(
    ["git", "rev-parse", "--verify", branch_name],
    capture_output=True,
    check=False,
    log_errors=False,   # failure = branch absent, fully expected
)
branch_exists = result.returncode == 0

# 2. First-try cleanup: remove worktree if it exists (no-op if absent)
try:
    run(["git", "worktree", "remove", str(worktree_path)], log_errors=False)
except CalledProcessError:
    pass  # Not yet created — expected on first run
```

### Test coverage

```bash
pixi run pytest tests/unit -v
# 1403 passed, 0 failed (CI: PR #301)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #301, branch port-circuit-breaker-success-threshold | 1403 tests pass in CI |
