# Improve Automation Error Visibility

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-14 |
| **Project** | ProjectScylla |
| **Issue** | #632 |
| **PR** | #633 |
| **Objective** | Make errors visible in curses UI and add granular status updates to automation scripts |
| **Outcome** | ✅ Success - All 211 tests passing, errors now visible in UI, 12+ granular status updates |

## When to Use

Use this skill when:
- **Error blindness**: Logger errors/warnings don't appear in curses UI "Recent Activity"
- **Coarse status updates**: UI shows only high-level phases (e.g., "Implementing") but users can't see sub-steps
- **Silent failures**: Worker slots go from active directly to "[idle]" with no failure indication
- **Missing context propagation**: Sub-methods can't update UI status because they lack slot_id/thread_id
- **Timeout issues**: CLI commands hang indefinitely without timeout protection
- **Incomplete exception handling**: Some exception types escape error handlers

**Key Indicators**:
- Zero visibility of `logger.error()` or `logger.warning()` in UI
- Users asking "what's happening?" during long operations
- Failed workers disappear without trace
- Exceptions escape and crash the whole script

## Verified Workflow

### 1. Add Dual-Logging Helper

Create a helper method that routes to both standard logger AND UI log manager:

```python
def _log(self, level: str, msg: str, thread_id: int | None = None) -> None:
    """Log to both standard logger and UI thread buffer."""
    getattr(logger, level)(msg)
    tid = thread_id or threading.get_ident()
    prefix = {"error": "ERROR", "warning": "WARN", "info": ""}.get(level, "")
    ui_msg = f"{prefix}: {msg}" if prefix else msg
    self.log_manager.log(tid, ui_msg)
```

**Use throughout code**:
```python
# Replace direct logger calls
self._log("error", f"Failed to implement issue #{issue_number}: {e}", thread_id)
self._log("warning", f"Retrospective failed: {e}", thread_id)
self._log("info", f"Issue #{issue_number} completed", thread_id)
```

### 2. Propagate Context IDs Through Method Chains

Add `slot_id` parameter to all sub-methods that need to update UI:

```python
# Parent method
def _implement_issue(self, issue_number: int) -> WorkerResult:
    slot_id = self.status_tracker.acquire_slot()
    thread_id = threading.get_ident()

    # Pass context to sub-methods
    self._run_claude_code(issue_number, worktree_path, prompt, slot_id=slot_id)
    self._ensure_pr_created(issue_number, branch_name, worktree_path, slot_id)
    self._run_retrospective(session_id, worktree_path, issue_number, slot_id)
    self._run_follow_up_issues(session_id, worktree_path, issue_number, slot_id)

# Sub-method signatures
def _run_claude_code(
    self, issue_number: int, worktree_path: Path, prompt: str, slot_id: int | None = None
) -> str | None:
    if slot_id is not None:
        self.status_tracker.update_slot(slot_id, f"#{issue_number}: Running Claude Code")
```

### 3. Add Granular Status Updates

Replace coarse 5-phase updates with 12+ granular sub-steps:

```python
# Worktree setup
self.status_tracker.update_slot(slot_id, f"#{issue_number}: Creating worktree")

# Plan phase (use ImplementationPhase.PLANNING)
self.status_tracker.update_slot(slot_id, f"#{issue_number}: Checking plan")
if not has_plan:
    state.phase = ImplementationPhase.PLANNING
    self.status_tracker.update_slot(slot_id, f"#{issue_number}: Generating plan")

# Fetch context
self.status_tracker.update_slot(slot_id, f"#{issue_number}: Fetching issue")

# Implementation (use ImplementationPhase.IMPLEMENTING)
state.phase = ImplementationPhase.IMPLEMENTING
self.status_tracker.update_slot(slot_id, f"#{issue_number}: Running Claude Code")

# PR creation (use ImplementationPhase.CREATING_PR)
state.phase = ImplementationPhase.CREATING_PR
self.status_tracker.update_slot(slot_id, f"#{issue_number}: Checking commit")
self.status_tracker.update_slot(slot_id, f"#{issue_number}: Pushing branch")
self.status_tracker.update_slot(slot_id, f"#{issue_number}: Creating PR")

# Retrospective (use ImplementationPhase.RETROSPECTIVE)
state.phase = ImplementationPhase.RETROSPECTIVE
self.status_tracker.update_slot(slot_id, f"#{issue_number}: Running retrospective")

# Follow-up (use ImplementationPhase.FOLLOW_UP_ISSUES)
state.phase = ImplementationPhase.FOLLOW_UP_ISSUES
self.status_tracker.update_slot(slot_id, f"#{issue_number}: Identifying follow-ups")
for i, item in enumerate(items, 1):
    self.status_tracker.update_slot(slot_id, f"#{issue_number}: Creating follow-up {i}/{len(items)}")
```

### 4. Classify Exceptions with Contextual Error Messages

Replace generic `except Exception` with classified handling:

```python
try:
    # Implementation logic
    pass

except subprocess.TimeoutExpired as e:
    error_msg = f"Timeout: {' '.join(e.cmd[:3])} exceeded {e.timeout}s"
    self._log("error", error_msg, thread_id)
    # Show in UI, save state, return failed result

except subprocess.CalledProcessError as e:
    error_msg = f"Command failed (exit {e.returncode}): {' '.join(e.cmd[:3])}"
    self._log("error", error_msg, thread_id)
    if e.stderr:
        self._log("error", f"stderr: {e.stderr[:300]}", thread_id)
    # Show in UI, save state, return failed result

except RuntimeError as e:
    self._log("error", f"Runtime error: {e}", thread_id)
    # Show in UI, save state, return failed result

except Exception as e:
    self._log("error", f"Unexpected {type(e).__name__}: {e}", thread_id)
    # Show in UI, save state, return failed result
```

### 5. Show Failure in UI Before Releasing Slot

Make failures visible by updating slot status before release:

```python
except Exception as e:
    error_msg = str(e)[:80]
    self._log("error", f"Failed: {e}", thread_id)

    # Show failure in UI BEFORE releasing
    self.status_tracker.update_slot(slot_id, f"#{issue_number}: FAILED - {error_msg[:50]}")

    # Save failure state
    state.phase = ImplementationPhase.FAILED
    state.error = str(e)
    self._save_state(state)

    return WorkerResult(issue_number=issue_number, success=False, error=str(e))

finally:
    # Brief pause so user sees failure status
    time.sleep(1)
    self.status_tracker.release_slot(slot_id)
```

### 6. Add Timeout Protection to CLI Calls

Prevent hanging by adding timeouts to all subprocess calls:

```python
# For gh CLI wrapper
result = run(
    ["gh"] + args,
    check=check,
    capture_output=True,
    timeout=120,  # 2 minute timeout
)

# For Claude Code
result = run(
    ["claude", str(prompt_file), ...],
    cwd=worktree_path,
    timeout=1800,  # 30 minute timeout
)
```

### 7. Broaden Exception Handling for Non-Critical Paths

For auto-merge and other optional features, catch all exceptions:

```python
# Before: Only caught CalledProcessError
if auto_merge:
    try:
        _gh_call(["pr", "merge", str(pr_number), "--auto", "--rebase"])
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to enable auto-merge: {e}")

# After: Catch all exceptions (RuntimeError from rate limit, etc.)
if auto_merge:
    try:
        _gh_call(["pr", "merge", str(pr_number), "--auto", "--rebase"])
    except Exception as e:
        logger.warning(f"Failed to enable auto-merge: {e}")
```

### 8. Comprehensive Test Coverage

Add tests for all new behaviors:

```python
# Test _log() helper routes to both logger and UI
def test_log_helper_routes_to_ui(implementer):
    with patch("module.logger") as mock_logger, \
         patch.object(implementer.log_manager, "log") as mock_log_manager:
        implementer._log("error", "Test error")
        mock_logger.error.assert_called_once_with("Test error")
        mock_log_manager.assert_called_once()
        assert "ERROR:" in str(mock_log_manager.call_args)

# Test failure shows in status slot
def test_failure_shows_in_status_slot(implementer):
    with patch.object(implementer.status_tracker, "update_slot") as mock_update:
        # Trigger failure
        result = implementer._implement_issue(123)
        # Verify "FAILED" appeared in status updates
        assert any("FAILED" in str(call) for call in mock_update.call_args_list)

# Test exception classification
def test_exception_classification_timeout(implementer):
    with patch.object(implementer, "_log") as mock_log:
        # Trigger TimeoutExpired
        result = implementer._implement_issue(123)
        # Verify "Timeout" appears in log calls
        assert any("Timeout" in str(call) for call in mock_log.call_args_list)

# Test granular status updates
def test_granular_status_updates(implementer):
    with patch.object(implementer.status_tracker, "update_slot") as mock_update:
        result = implementer._implement_issue(123)
        messages = [str(call) for call in mock_update.call_args_list]
        # Check for 12+ distinct status messages
        assert len(messages) >= 12
        assert any("Creating worktree" in msg for msg in messages)
        assert any("Running Claude Code" in msg for msg in messages)
```

## Failed Attempts

### ❌ Creating a Separate Logging Module

**Attempt**: Created a separate `ui_logger.py` module with dual-logging functions.

**Why it failed**:
- Added unnecessary complexity and indirection
- Required importing in multiple files
- Made it harder to trace where logs were coming from
- The helper method pattern was simpler and kept everything in one place

**What worked instead**: Adding `_log()` as a method on the class itself - single responsibility, easy to understand, no extra imports.

### ❌ Using Mock Unused Variables in Tests

**Attempt**: Kept `mock_update` variable even when not used for assertions.

**Why it failed**:
- Pre-commit ruff check failed with F841 (unused variable)
- Created unnecessary noise in test code

**What worked instead**: Remove the `as mock_update` binding when the mock isn't needed for assertions - cleaner code that passes linting.

## Results & Parameters

### Final Configuration

```python
# Timeout values
GH_CLI_TIMEOUT = 120      # 2 minutes for gh commands
CLAUDE_TIMEOUT = 1800     # 30 minutes for Claude Code
RETROSPECTIVE_TIMEOUT = 600  # 10 minutes for retrospective

# UI display
FAILURE_PAUSE = 1         # Seconds to show failure before releasing slot
ERROR_TRUNCATE = 50       # Characters for error display in status slot
STDERR_TRUNCATE = 300     # Characters for stderr in logs

# Log prefixes
LOG_PREFIXES = {
    "error": "ERROR",
    "warning": "WARN",
    "info": ""
}
```

### Test Results

```bash
# All automation tests pass
$ pixi run python -m pytest tests/unit/automation/ -v
============================= test session starts ==============================
...
============================== 211 passed in 14.11s =============================

# Pre-commit hooks pass
$ pre-commit run --all-files
Check for shell=True (Security)..........................................Passed
Ruff Format Python.......................................................Passed
Ruff Check Python........................................................Passed
...
```

### Status Update Progression

**Before (5 updates)**:
1. "Issue #123: Starting"
2. "Issue #123: Implementing"
3. "Issue #123: Verifying"
4. "Issue #123: Retrospective"
5. "Issue #123: Follow-up issues"

**After (12+ updates)**:
1. "#123: Creating worktree"
2. "#123: Checking plan"
3. "#123: Generating plan" (conditional)
4. "#123: Fetching issue"
5. "#123: Running Claude Code"
6. "#123: Checking commit"
7. "#123: Pushing branch"
8. "#123: Creating PR"
9. "#123: Running retrospective"
10. "#123: Identifying follow-ups"
11. "#123: Creating follow-up 1/N"
12. "#123: Creating follow-up N/N"

### Error Visibility Comparison

**Before**:
- UI "Recent Activity": 3 info messages only
- Logger output: ~40 error/warning messages (invisible to UI)
- Failed worker: Disappears silently to "[idle]"

**After**:
- UI "Recent Activity": All errors and warnings visible with prefixes
- Logger output: Same ~40 messages (still in logs)
- Failed worker: Shows "FAILED - {error}" for 1 second before "[idle]"

## Key Learnings

1. **Dual-logging pattern is powerful**: Route critical messages to both structured logging AND user-visible UI
2. **Context propagation is essential**: Pass `slot_id`/`thread_id` through call chains for observability
3. **Classify exceptions by type**: Different exception types need different error messages and handling
4. **Show failures before cleanup**: Always display error state before releasing resources
5. **Timeout everything**: Any external process call should have a timeout
6. **Test the observability**: Error visibility needs explicit test coverage
7. **Keep it simple**: Helper methods > separate modules for simple cross-cutting concerns

## Related Skills

- `parallel-worktree-workflow` - Worker pool pattern used in implementer
- `checkpoint-recovery` - State persistence and resume capability
- `investigate-test-failures` - Testing patterns and coverage strategies
- `python-subprocess-terminal-corruption` - Subprocess handling best practices

## References

- Issue: https://github.com/HomericIntelligence/ProjectScylla/issues/632
- PR: https://github.com/HomericIntelligence/ProjectScylla/pull/633
- Files modified:
  - `scylla/automation/implementer.py`
  - `scylla/automation/github_api.py`
  - `tests/unit/automation/test_implementer.py`
  - `tests/unit/automation/test_github_api_errors.py` (new)
