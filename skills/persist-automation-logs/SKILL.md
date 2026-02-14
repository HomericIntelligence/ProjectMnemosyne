# Persist Automation Logs for Post-Mortem Analysis

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-14 |
| **Project** | ProjectScylla |
| **Issue** | #602 |
| **PR** | TBD |
| **Objective** | Persist execution logs (Claude Code output, retrospective, follow-up) to disk even after worktrees are cleaned up |
| **Outcome** | ✅ Success - All 30 tests passing, logs persisted to `.issue_implementer/` directory |

## When to Use

Use this skill when:
- **Silent failures after cleanup**: Automation script fails, worktrees are cleaned up, and there's no way to debug what happened
- **Curses UI hides output**: When using curses UI, Claude Code stdout/stderr is invisible until the process completes
- **Non-blocking phases fail**: Retrospective or follow-up phases fail silently (logged to stderr but not persisted)
- **Need post-mortem analysis**: You need to analyze what happened after the script has exited and cleaned up all temporary state

**Key Indicators**:
- Logger warnings like `"Retrospective failed for issue #123: {error}"` but no way to see the actual error details
- Worktree cleanup (`worktree_manager.cleanup_all()`) destroys all evidence of what went wrong
- No log files exist in `.issue_implementer/` except state JSON files

**Related Skills**:
- `improve-automation-error-visibility`: Complements this by making errors visible in curses UI *during* execution
- This skill focuses on *persisting* logs for *after* execution completes

## Verified Workflow

### 1. Add File Logging to Main Script

Add a `FileHandler` to the Python logger to capture all stderr/stdout to a file:

**File**: `scripts/implement_issues.py`

```python
from pathlib import Path

def setup_logging(verbose: bool = False, log_dir: Path | None = None) -> None:
    """Configure logging.

    Args:
        verbose: Enable verbose (DEBUG) logging
        log_dir: Optional directory to write log files
    """
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(level=level, format=fmt, datefmt=datefmt)

    # Add file handler if log_dir provided
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / "run.log", mode="a")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
        logging.getLogger().addHandler(fh)

def main() -> int:
    args = parse_args()

    # Set up logging with file handler
    from scylla.automation.git_utils import get_repo_root
    state_dir = get_repo_root() / ".issue_implementer"
    setup_logging(args.verbose, log_dir=state_dir)
    # ... rest of main
```

**Result**: All `logger.info()`, `logger.warning()`, `logger.error()` calls are written to `.issue_implementer/run.log`

### 2. Save Claude Code Output on Success AND Failure

**File**: `scylla/automation/implementer.py`, method `_run_claude_code()`

Add `state_dir.mkdir()` at the start to ensure directory exists:

```python
def _run_claude_code(self, issue_number: int, worktree_path: Path, prompt: str) -> str | None:
    if self.options.dry_run:
        return None

    self.state_dir.mkdir(parents=True, exist_ok=True)  # Ensure directory exists

    # ... write prompt and run Claude
```

**On success** (after parsing JSON):

```python
try:
    data = json.loads(result.stdout)
    session_id = data.get("session_id")

    # Save successful output to log file
    log_file = self.state_dir / f"claude-{issue_number}.log"
    log_file.write_text(result.stdout or "")

    return session_id
except (json.JSONDecodeError, AttributeError):
    logger.warning(f"Could not parse session_id for issue #{issue_number}")

    # Save output even if JSON parsing failed
    log_file = self.state_dir / f"claude-{issue_number}.log"
    log_file.write_text(result.stdout or "")

    return None
```

**On CalledProcessError**:

```python
except subprocess.CalledProcessError as e:
    logger.error(f"Claude Code failed for issue #{issue_number}")
    logger.error(f"Exit code: {e.returncode}")

    # Save failure output to log file
    log_file = self.state_dir / f"claude-{issue_number}.log"
    stdout = e.stdout or ""
    stderr = e.stderr or ""
    output = f"EXIT CODE: {e.returncode}\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
    log_file.write_text(output)

    raise RuntimeError(f"Claude Code failed: {e.stderr or e.stdout}") from e
```

**On TimeoutExpired**:

```python
except subprocess.TimeoutExpired as e:
    # Save timeout info to log file
    log_file = self.state_dir / f"claude-{issue_number}.log"
    log_file.write_text(f"TIMEOUT after {e.timeout}s\n\nOutput:\n{e.output or ''}")

    raise RuntimeError("Claude Code timed out") from e
```

### 3. Save Retrospective Output on Failure

**File**: `scylla/automation/implementer.py`, method `_run_retrospective()`

Add `state_dir.mkdir()` and save failure output:

```python
def _run_retrospective(self, session_id: str, worktree_path: Path, issue_number: int) -> None:
    """Resume Claude session to run /retrospective."""
    self.state_dir.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
    log_file = self.state_dir / f"retrospective-{issue_number}.log"

    try:
        result = run([
            "claude", "--resume", session_id,
            "/skills-registry-commands:retrospective commit the results and create a PR",
            "--print", "--permission-mode", "dontAsk",
            "--allowedTools", "Read,Write,Edit,Glob,Grep,Bash",
        ], cwd=self.repo_root, timeout=600)

        # Write output to log file
        log_file.write_text(result.stdout or "")
        logger.info(f"Retrospective completed for issue #{issue_number}")
        logger.info(f"Retrospective log: {log_file}")

    except Exception as e:
        logger.warning(f"Retrospective failed for issue #{issue_number}: {e}")

        # Save failure output to log file
        error_output = f"FAILED: {e}\n"
        if hasattr(e, "stdout"):
            error_output += f"\nSTDOUT:\n{e.stdout or ''}"
        if hasattr(e, "stderr"):
            error_output += f"\nSTDERR:\n{e.stderr or ''}"
        log_file.write_text(error_output)

        # Non-blocking: never re-raise
```

### 4. Save Follow-Up Issues Output

**File**: `scylla/automation/implementer.py`, method `_run_follow_up_issues()`

Add `state_dir.mkdir()`, save on success, and save on failure:

```python
def _run_follow_up_issues(self, session_id: str, worktree_path: Path, issue_number: int) -> None:
    """Resume Claude session to identify and file follow-up issues."""
    self.state_dir.mkdir(parents=True, exist_ok=True)  # Ensure directory exists

    # ... write prompt

    try:
        result = run([...], cwd=worktree_path, timeout=600)

        # Save successful output to log file
        follow_up_log = self.state_dir / f"follow-up-{issue_number}.log"
        follow_up_log.write_text(result.stdout or "")

        # Parse JSON output and create issues...

    except Exception as e:
        logger.warning(f"Follow-up issues failed for issue #{issue_number}: {e}")

        # Save failure output to log file
        follow_up_log = self.state_dir / f"follow-up-{issue_number}.log"
        error_output = f"FAILED: {e}\n"
        if hasattr(e, "stdout"):
            error_output += f"\nSTDOUT:\n{e.stdout or ''}"
        if hasattr(e, "stderr"):
            error_output += f"\nSTDERR:\n{e.stderr or ''}"
        follow_up_log.write_text(error_output)

        # Non-blocking: never re-raise
```

### 5. Add Test Coverage

Create tests to verify log persistence on both success and failure paths:

**File**: `tests/unit/automation/test_implementer.py`

```python
def test_claude_code_output_saved_to_log(self, implementer, tmp_path):
    """Test that Claude Code stdout is saved to log file on success."""
    implementer.state_dir = tmp_path
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir(exist_ok=True)

    mock_result = MagicMock()
    mock_result.stdout = json.dumps({
        "session_id": "test-session-123",
        "result": "Implementation complete",
    })

    with patch("scylla.automation.implementer.run") as mock_run:
        mock_run.return_value = mock_result

        implementer._run_claude_code(123, worktree_path, "Implement issue")

        # Verify log file was created and contains stdout
        log_file = tmp_path / "claude-123.log"
        assert log_file.exists()
        assert "test-session-123" in log_file.read_text()

def test_claude_code_failure_saved_to_log(self, implementer, tmp_path):
    """Test that Claude Code failure output is saved to log file."""
    implementer.state_dir = tmp_path
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir(exist_ok=True)

    with patch("scylla.automation.implementer.run") as mock_run:
        error = subprocess.CalledProcessError(
            returncode=1, cmd=["claude"],
            output="Some output", stderr="Error message"
        )
        error.stdout = "Claude stdout output"
        error.stderr = "Claude stderr output"
        mock_run.side_effect = error

        with pytest.raises(RuntimeError, match="Claude Code failed"):
            implementer._run_claude_code(456, worktree_path, "Implement issue")

        # Verify log file contains failure details
        log_file = tmp_path / "claude-456.log"
        assert log_file.exists()
        content = log_file.read_text()
        assert "EXIT CODE: 1" in content
        assert "Claude stdout output" in content
        assert "Claude stderr output" in content
```

Similar tests for retrospective and follow-up phases.

**Important**: Update existing tests to use `tmp_path` for `state_dir`:

```python
def test_existing_test(self, implementer, tmp_path):
    """Existing test that needs state_dir."""
    implementer.state_dir = tmp_path  # Add this line
    # ... rest of test
```

## Failed Attempts

| Approach | Why It Failed | Solution |
|----------|---------------|----------|
| Patch `Path.write_text` globally in tests | Caused recursion - patched `write_text` called real `write_text` which called patched version infinitely | Don't patch `write_text`, just use real file I/O with `tmp_path` |
| Write log files without `mkdir()` | `FileNotFoundError` when state_dir doesn't exist (common in tests) | Always call `self.state_dir.mkdir(parents=True, exist_ok=True)` before writing |
| Mock state_dir as `/repo/.issue_implementer` | Tests failed with permission errors trying to create `/repo` directory | Use `tmp_path` fixture and set `implementer.state_dir = tmp_path` |
| Only save logs on success | Defeats the purpose - failures are what need debugging | Save logs on ALL exit paths: success, CalledProcessError, TimeoutExpired, generic Exception |

## Results & Parameters

### Files Created After Implementation

After running `scripts/implement_issues.py`, the `.issue_implementer/` directory contains:

```
.issue_implementer/
├── run.log                      # Full Python logger output (all phases, all issues)
├── claude-123.log               # Claude Code output for issue #123
├── claude-456.log               # Claude Code output for issue #456
├── retrospective-123.log        # Retrospective output for issue #123
├── follow-up-123.log            # Follow-up issues output for issue #123
├── issue-123.json               # State file for issue #123
└── issue-456.json               # State file for issue #456
```

### Test Results

- **Before**: 24 tests passing
- **After**: 30 tests passing (added 5 new tests, updated 10 existing tests)
- **Coverage**: All three execution phases (Claude Code, retrospective, follow-up) tested for both success and failure paths

### Log File Formats

**Claude Code success**:
```json
{
  "type": "result",
  "session_id": "abc123-def456",
  "result": "Implementation complete",
  "total_cost_usd": 0.13
}
```

**Claude Code failure**:
```
EXIT CODE: 1

STDOUT:
<claude stdout output>

STDERR:
<claude stderr output>
```

**Retrospective/Follow-up failure**:
```
FAILED: [Error message]

STDOUT:
<process stdout if available>

STDERR:
<process stderr if available>
```

## Key Learnings

1. **Ensure directory exists before writing**: Always call `mkdir(parents=True, exist_ok=True)` before writing log files, especially in tests
2. **Save on ALL exit paths**: Don't just save on success - failures are what need debugging
3. **Don't patch file I/O in tests**: Use real file I/O with `tmp_path` instead of mocking `Path.write_text`
4. **Separate concerns**: `FileHandler` for Python logs, individual log files for subprocess output
5. **Test both success and failure**: Verify logs are persisted in all scenarios

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #602, PR TBD | [notes.md](../references/notes.md) |
