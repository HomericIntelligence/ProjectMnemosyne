# Implementation Notes: Persist Automation Logs

## Session Context

**Date**: 2026-02-14
**Project**: ProjectScylla
**Issue**: #602 - Persist execution logs for post-mortem analysis
**Objective**: Ensure all execution logs (Claude Code output, retrospective, follow-up) are persisted to `.issue_implementer/` so failures can be analyzed even after worktrees are cleaned up

## Problem Statement

When `implement_issues.py` runs with the curses UI, execution logs are either lost entirely or only saved on success:

1. **Claude Code output**: Only visible in curses UI during execution, lost after process completes
2. **Retrospective output**: When it fails, only a `logger.warning()` goes to stderr (invisible with curses UI active)
3. **Follow-up output**: Similar issue - failures are logged but not persisted
4. **Worktree cleanup**: After run completes, `worktree_manager.cleanup_all()` destroys all evidence

**Trigger Case**: User ran script for issue #602, retrospective phase failed silently, worktree cleaned up → no way to debug.

## Implementation Details

### Files Modified

1. **scripts/implement_issues.py**
   - Added `Path` import for type hints
   - Updated `setup_logging()` to accept `log_dir: Path | None` parameter
   - Added `FileHandler` to write all logger output to `{log_dir}/run.log`
   - Modified `main()` to compute `state_dir` and pass to `setup_logging()`

2. **scylla/automation/implementer.py**
   - `_run_claude_code()`: Added log file persistence on success, CalledProcessError, and TimeoutExpired
   - `_run_retrospective()`: Added log file persistence on failure
   - `_run_follow_up_issues()`: Added log file persistence on success and failure
   - All methods: Added `self.state_dir.mkdir(parents=True, exist_ok=True)` before writing

3. **tests/unit/automation/test_implementer.py**
   - Added 5 new tests for log file persistence
   - Updated 10 existing tests to use `tmp_path` for `state_dir` instead of `/repo/.issue_implementer`

### Code Patterns

#### Pattern 1: FileHandler for Python Logs

```python
if log_dir:
    log_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_dir / "run.log", mode="a")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    logging.getLogger().addHandler(fh)
```

**Why**: Captures all `logger.info/warning/error()` calls to a persistent file.

#### Pattern 2: Save Subprocess Output on All Exit Paths

```python
try:
    result = run([...], timeout=timeout)

    # Save successful output
    log_file = self.state_dir / f"phase-{issue_number}.log"
    log_file.write_text(result.stdout or "")

    # ... process result ...

except subprocess.CalledProcessError as e:
    # Save failure output
    log_file = self.state_dir / f"phase-{issue_number}.log"
    stdout = e.stdout or ""
    stderr = e.stderr or ""
    output = f"EXIT CODE: {e.returncode}\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
    log_file.write_text(output)
    raise

except subprocess.TimeoutExpired as e:
    # Save timeout info
    log_file = self.state_dir / f"phase-{issue_number}.log"
    log_file.write_text(f"TIMEOUT after {e.timeout}s\n\nOutput:\n{e.output or ''}")
    raise
```

**Why**: Ensures logs are persisted regardless of how the subprocess exits.

#### Pattern 3: Ensure Directory Exists Before Writing

```python
def _run_phase(self, ...):
    self.state_dir.mkdir(parents=True, exist_ok=True)  # Always first
    log_file = self.state_dir / f"phase-{issue_number}.log"
    # ... write to log_file ...
```

**Why**: Prevents `FileNotFoundError` when directory doesn't exist (common in tests).

## Test Approach

### Testing File I/O

**Don't patch `Path.write_text`**: Caused infinite recursion when implementation tried to write.

**Do use real file I/O with `tmp_path`**:

```python
def test_output_saved(self, implementer, tmp_path):
    implementer.state_dir = tmp_path
    implementer.state_dir.mkdir(exist_ok=True)

    # ... run code that writes logs ...

    log_file = tmp_path / "output.log"
    assert log_file.exists()
    assert "expected content" in log_file.read_text()
```

### Updating Existing Tests

Many existing tests had `state_dir = Path("/repo/.issue_implementer")` from fixture, which doesn't exist. Solution:

```python
def test_existing(self, implementer, tmp_path):
    implementer.state_dir = tmp_path  # Override with tmp_path
    # ... rest of test unchanged ...
```

## Log File Outputs

After a real run, `.issue_implementer/` contains:

```
.issue_implementer/
├── run.log                      # All Python logger output
├── claude-{N}.log               # Claude Code output per issue
├── retrospective-{N}.log        # Retrospective output per issue
├── follow-up-{N}.log            # Follow-up issues output per issue
└── issue-{N}.json               # State files (already existed)
```

### Example Log Formats

**Claude Code success** (`claude-123.log`):
```json
{
  "type": "result",
  "session_id": "abc123-def456",
  "result": "Implementation complete",
  "total_cost_usd": 0.13
}
```

**Claude Code failure** (`claude-456.log`):
```
EXIT CODE: 1

STDOUT:
<full stdout from Claude>

STDERR:
<full stderr from Claude>
```

**Retrospective failure** (`retrospective-789.log`):
```
FAILED: CalledProcessError(...)

STDOUT:
<retrospective output if available>

STDERR:
<error details if available>
```

## Debugging the Original Issue

With logs persisted, the original issue (#602 - retrospective failed for issue #602) can now be debugged:

1. Check `run.log` for high-level timeline and error messages
2. Check `retrospective-602.log` for detailed failure output
3. If Claude Code also failed, check `claude-602.log` for root cause
4. State file `issue-602.json` shows which phase it failed in

## Test Results

- **Before**: 24 tests passing
- **After**: 30 tests passing
- **New tests**: 5 (log persistence verification)
- **Updated tests**: 10 (use `tmp_path` for `state_dir`)

All tests pass, pre-commit hooks pass (ruff format, ruff check).

## Related Work

- **Issue #632**: Improve automation error visibility (curses UI dual logging)
- **PR #633**: Implemented dual logging and granular status updates

This skill (#602) is complementary:
- #632 makes errors **visible during execution** (curses UI)
- #602 makes errors **analyzable after execution** (log files)

## Key Decisions

1. **Why separate log files per phase?**
   - Easier to find specific failure (claude vs retrospective vs follow-up)
   - Prevents mixing different subprocess outputs

2. **Why `mkdir()` in every method?**
   - Tests often don't have state_dir set up
   - Defensive programming - prevents silent failures

3. **Why save on failure paths?**
   - Failures are what need debugging
   - Success paths are nice-to-have for completeness

4. **Why not use a context manager?**
   - Subprocess output isn't available until after completion
   - Need to write in exception handlers, not just try block

## Performance Impact

- Negligible: Writing small log files (<1MB each typically)
- `mkdir(parents=True, exist_ok=True)` is idempotent and fast
- File I/O is non-blocking (happens after subprocess completes)

## Future Enhancements

Potential improvements (not implemented):

1. **Log rotation**: Cap log file sizes, delete old runs
2. **Structured logging**: JSON format for easier parsing
3. **Aggregated summary**: Single file with all issues' status
4. **Compression**: gzip old log files to save space
5. **Log viewer UI**: Terminal UI to browse logs interactively
