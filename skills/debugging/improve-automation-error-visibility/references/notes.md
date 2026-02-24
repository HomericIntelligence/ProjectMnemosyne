# Implementation Notes: Improve Automation Error Visibility

## Session Context

**Date**: 2026-02-14
**Project**: ProjectScylla
**Issue**: #632
**PR**: #633
**Objective**: Make errors visible in curses UI and add granular status updates

## Problem Statement

The `implement_issues.py` script with curses UI had zero error visibility:
- ~40 `logger.error()` and `logger.warning()` calls in `implementer.py`
- Only 3 informational messages ever reached the UI via `log_manager.log()`
- Failed workers went from last phase (e.g., "Implementing") directly to "[idle]" with no failure indication
- Status updates were coarse: only 5 phases vs 10 enum values available
- Sub-methods couldn't update UI because they lacked `slot_id`/`thread_id` parameters
- GitHub CLI auto-merge exception handling was too narrow (only caught `CalledProcessError`, not `RuntimeError`)
- No timeout on gh CLI calls could cause indefinite hangs

## Implementation Details

### 1. Dual-Logging Helper (`_log()`)

Added as instance method on `IssueImplementer` class:

```python
def _log(self, level: str, msg: str, thread_id: int | None = None) -> None:
    """Log to both standard logger and UI thread buffer."""
    getattr(logger, level)(msg)
    tid = thread_id or threading.get_ident()
    prefix = {"error": "ERROR", "warning": "WARN", "info": ""}.get(level, "")
    ui_msg = f"{prefix}: {msg}" if prefix else msg
    self.log_manager.log(tid, ui_msg)
```

**Design decisions**:
- Instance method (not module-level function) for access to `self.log_manager`
- Automatic thread ID resolution via `threading.get_ident()`
- Prefix only for error/warning (info messages unprefixed for readability)
- Uses `getattr()` for dynamic logger method resolution

### 2. Context Propagation

Added `slot_id: int | None = None` parameter to:
- `_run_claude_code()`
- `_ensure_pr_created()`
- `_run_retrospective()`
- `_run_follow_up_issues()`

**Pattern**:
```python
if slot_id is not None:
    self.status_tracker.update_slot(slot_id, f"#{issue_number}: {sub_step}")
```

### 3. Granular Status Updates

Mapped status updates to unused `ImplementationPhase` enum values:

| Phase | Status Messages |
|-------|-----------------|
| PLANNING | "Checking plan", "Generating plan" |
| IMPLEMENTING | "Fetching issue", "Running Claude Code" |
| CREATING_PR | "Checking commit", "Pushing branch", "Creating PR" |
| RETROSPECTIVE | "Running retrospective" |
| FOLLOW_UP_ISSUES | "Identifying follow-ups", "Creating follow-up X/N" |

### 4. Exception Classification

Four-tier exception handling in `_implement_issue()`:

```python
except subprocess.TimeoutExpired as e:
    error_msg = f"Timeout: {' '.join(e.cmd[:3])} exceeded {e.timeout}s"
    # ...

except subprocess.CalledProcessError as e:
    error_msg = f"Command failed (exit {e.returncode}): {' '.join(e.cmd[:3])}"
    if e.stderr:
        self._log("error", f"stderr: {e.stderr[:300]}", thread_id)
    # ...

except RuntimeError as e:
    self._log("error", f"Runtime error: {e}", thread_id)
    # ...

except Exception as e:
    self._log("error", f"Unexpected {type(e).__name__}: {e}", thread_id)
    # ...
```

All branches:
1. Create descriptive error message
2. Log via `_log()` to both logger and UI
3. Update slot with "FAILED - {error[:50]}"
4. Set `state.phase = ImplementationPhase.FAILED`
5. Save state to disk
6. Return `WorkerResult(success=False, error=...)`

### 5. Failure Display Before Cleanup

```python
finally:
    # Brief pause so UI shows final status before going idle
    time.sleep(1)
    self.status_tracker.release_slot(slot_id)
```

1-second pause ensures users see "FAILED - ..." status before slot goes to "[idle]"

### 6. Timeout Protection

Added to `_gh_call()` in `github_api.py`:

```python
result = run(
    ["gh"] + args,
    check=check,
    capture_output=True,
    timeout=120,  # 2 minute timeout for gh CLI calls
)
```

### 7. Broadened Auto-Merge Exception Handling

**Before** (`github_api.py:254`):
```python
except subprocess.CalledProcessError as e:
    logger.warning(f"Failed to enable auto-merge: {e}")
```

**After**:
```python
except Exception as e:
    logger.warning(f"Failed to enable auto-merge: {e}")
```

Catches `RuntimeError` raised by `_gh_call()` when rate limit detected.

## Test Coverage

### New Test Classes

1. **`TestLogHelper`** (4 tests)
   - `test_log_helper_routes_to_ui` - Verifies dual logging
   - `test_log_helper_warning_level` - Tests "WARN" prefix
   - `test_log_helper_info_level` - Tests no prefix for info
   - `test_log_helper_custom_thread_id` - Tests explicit thread_id

2. **`TestErrorVisibility`** (3 tests)
   - `test_failure_shows_in_status_slot` - Verifies "FAILED" in slot updates
   - `test_exception_classification_timeout` - Tests `TimeoutExpired` handling
   - `test_exception_classification_called_process_error` - Tests command failure handling

3. **`TestGranularStatusUpdates`** (1 test)
   - `test_granular_status_updates` - Verifies 12+ status messages with key sub-steps

4. **`TestAutoMergeErrorHandling`** (2 tests in `test_github_api_errors.py`)
   - `test_auto_merge_runtime_error_caught` - Tests `RuntimeError` doesn't escape
   - `test_auto_merge_called_process_error_caught` - Tests `CalledProcessError` handling

5. **`TestGhCallTimeout`** (2 tests in `test_github_api_errors.py`)
   - `test_gh_call_timeout` - Verifies timeout parameter passed
   - `test_gh_call_timeout_expired` - Verifies `TimeoutExpired` propagation

### Updated Tests

- `test_successful_retrospective` - Added `slot_id=None` parameter to match new signature

### Test Results

```
tests/unit/automation/test_implementer.py::TestLogHelper - 4 passed
tests/unit/automation/test_implementer.py::TestErrorVisibility - 3 passed
tests/unit/automation/test_implementer.py::TestGranularStatusUpdates - 1 passed
tests/unit/automation/test_github_api_errors.py - 4 passed
...
============================== 211 passed in 14.11s =============================
```

## Code Changes Summary

### `scylla/automation/implementer.py`

**Lines added**: ~150
**Lines modified**: ~30

Key additions:
- Line 77-91: `_log()` helper method
- Line 663-677: Updated `_run_claude_code()` signature with `slot_id`
- Line 819-834: Updated `_ensure_pr_created()` signature with granular status updates
- Line 730-740: Updated `_run_retrospective()` signature
- Line 540-550: Updated `_run_follow_up_issues()` signature
- Line 345-370: Granular status updates in `_implement_issue()` (worktree, plan, fetch)
- Line 437-512: Four-tier exception classification with failure display

### `scylla/automation/github_api.py`

**Lines modified**: 2

Key changes:
- Line 56: Added `timeout=120` to `_gh_call()` subprocess
- Line 254: Changed `except subprocess.CalledProcessError` to `except Exception`

### `tests/unit/automation/test_implementer.py`

**Lines added**: ~180

Key additions:
- Line 650-700: `TestLogHelper` class (4 tests)
- Line 702-780: `TestErrorVisibility` class (3 tests)
- Line 782-850: `TestGranularStatusUpdates` class (1 test)

### `tests/unit/automation/test_github_api_errors.py`

**New file**: 69 lines

Classes:
- `TestAutoMergeErrorHandling` (2 tests)
- `TestGhCallTimeout` (2 tests)

## Pre-commit Hook Results

All hooks passed:
- ✅ Check for shell=True (Security)
- ✅ Ruff Format Python
- ✅ Ruff Check Python
- ✅ Trim Trailing Whitespace
- ✅ Fix End of Files
- ✅ Check for Large Files
- ✅ Fix Mixed Line Endings

Initial run required one fix:
- F841: Removed unused `mock_update` variable in `test_exception_classification_timeout`

## Deployment

Branch: `632-improve-error-handling-ui-status`
Commit: `8ce2a0e`
PR: https://github.com/HomericIntelligence/ProjectScylla/pull/633
Auto-merge: Enabled (rebase strategy)

## Lessons Learned

1. **Simple > Complex**: Helper method on class beat separate logging module
2. **Context is king**: Passing `slot_id` through call chains enabled fine-grained observability
3. **Test observability**: Error visibility needs explicit test coverage, not just functional tests
4. **Classify exceptions**: Different exception types need different error messages
5. **User experience matters**: 1-second pause to show failure status makes errors discoverable
6. **Timeout everything**: External CLI calls should always have timeouts
7. **Catch broadly for optional features**: Auto-merge and other non-critical paths should catch all exceptions

## Future Improvements

Potential enhancements not included in this PR:

1. **Configurable log levels**: Allow users to filter UI messages by severity
2. **Persistent error log**: Write UI-visible errors to dedicated log file
3. **Structured error tracking**: Collect error frequencies and patterns
4. **Progress bars**: Show percentage complete for multi-step operations
5. **Elapsed time tracking**: Show duration for each phase in status slot
6. **Retry visibility**: Show retry attempts in UI when auto-retry kicks in
