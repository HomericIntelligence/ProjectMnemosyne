---
name: observability-logging-and-process-monitoring
description: "Add structured observability to Python/shell pipelines. Use when: (1) adding JSON log formatting to a shared library for Loki/Promtail/ELK integration, (2) adding stage logging with timing to multi-stage pipeline workers, (3) implementing SIGINT/SIGTERM graceful shutdown with checkpoint save, (4) adding real-time progress indicators to parallel tier execution, (5) suppressing noisy ERROR logs for subprocess failures that callers intentionally catch, (6) adding a log level function to a shared bash logging library, (7) overwriting transient terminal status lines with carriage return, (8) extracting duplicate logger.info/warning blocks into a shared helper method."
category: tooling
date: 2026-05-19
version: "1.0.0"
user-invocable: false
history: observability-logging-and-process-monitoring.history
tags:
  - logging
  - observability
  - json
  - stdlib
  - stage-logging
  - signals
  - shutdown
  - checkpoint
  - progress
  - subprocess
  - log-suppress
  - shell
  - terminal
  - carriage-return
  - refactoring
  - dry
---

# Observability, Logging, and Process Monitoring

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-19 |
| **Objective** | Synthesise eight skills covering the observability layer of running processes: structured JSON logging, stage logging, graceful signal handling, tier progress indicators, subprocess log suppression, shell log levels, inline terminal status, and logging helper extraction |
| **Outcome** | Merged canonical — verified across ProjectHephaestus, ProjectScylla, Odysseus |
| **Verification** | verified-ci (members individually verified) |

## When to Use

- **JSON log formatting**: Adding structured JSON logging to a Python project without new dependencies; integrating with Loki/Promtail/ELK/Datadog
- **Stage logging**: Parallel workers execute multi-stage pipelines and logs show silent gaps ("appears hung"); need per-stage timing
- **Graceful shutdown**: Long-running process must handle Ctrl+C / SIGTERM, save a checkpoint, and return partial results
- **Tier progress**: Parallel execution shows no output for tens of seconds; users cannot tell if process is stuck
- **Subprocess log suppression**: `run_subprocess()` / `git_utils.run()` emits ERROR logs for failures the caller already catches; the errors are expected noise
- **Shell log level**: A bash logging library defines a color variable (`BLUE`) but no function uses it; need `log_debug()`
- **Inline terminal status**: A console tool floods the terminal with repeated transient status lines (DISCONNECTED, RECONNECTING); need `\r` overwrite
- **Extract logging helper**: Identical `logger.info/warning` blocks appear in 2+ branches; a DRY review comment flags them

## Verified Workflow

### Quick Reference

#### 1. Zero-Dependency JSON Log Formatter (Python stdlib)

```python
import json, logging, traceback
from datetime import datetime, timezone

class JsonFormatter(logging.Formatter):
    RESERVED = frozenset({"timestamp", "level", "logger", "message", "exception", "stack_info"})
    _DEFAULT_ATTRS = frozenset(
        logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
        | {"message", "msg", "args"}
    )

    def format(self, record: logging.LogRecord) -> str:
        log_dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extras = {k: v for k, v in record.__dict__.items() if k not in self._DEFAULT_ATTRS}
        for key, value in extras.items():
            log_dict[f"ctx_{key}" if key in self.RESERVED else key] = value
        if record.exc_info and record.exc_info[0] is not None:
            log_dict["exception"] = "".join(traceback.format_exception(*record.exc_info))
        if record.stack_info:
            log_dict["stack_info"] = record.stack_info
        return json.dumps(log_dict, default=str)

# Opt-in integration (backward compatible)
def get_logger(name: str, json_format: bool = False) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter() if json_format else logging.Formatter())
        logger.addHandler(handler)
    return logger
```

#### 2. Execution Stage Logging with Timing

```python
from enum import Enum
import time
from datetime import UTC, datetime

class ExecutionStage(str, Enum):
    WORKTREE = "WORKTREE"
    AGENT = "AGENT"
    JUDGE = "JUDGE"
    CLEANUP = "CLEANUP"
    COMPLETE = "COMPLETE"

def _stage_log(worker_id: str, stage: ExecutionStage, status: str,
               elapsed: float | None = None) -> None:
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    suffix = f" ({elapsed:.1f}s)" if elapsed is not None else ""
    logger.info(f"{ts} [{worker_id}] Stage: {stage.value} - {status}{suffix}")

# Usage pattern
start = time.time()
_stage_log(worker_id, ExecutionStage.AGENT, "Starting")
agent_start = time.time()
# ... work ...
_stage_log(worker_id, ExecutionStage.AGENT, "Complete", time.time() - agent_start)
_stage_log(worker_id, ExecutionStage.COMPLETE, "All stages complete", time.time() - start)
```

#### 3. Graceful SIGINT/SIGTERM with Checkpoint

```python
import signal

_shutdown_requested = False

def request_shutdown() -> None:
    global _shutdown_requested
    _shutdown_requested = True
    logger.warning("Graceful shutdown requested")

def is_shutdown_requested() -> bool:
    return _shutdown_requested

# Register in main()
def _signal_handler(signum: int, frame) -> None:
    logger.warning(f"Received signal {signum}, initiating graceful shutdown...")
    request_shutdown()

signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

# Check at tier/task boundaries
for tier_id in config.tiers_to_run:
    if is_shutdown_requested():
        logger.warning(f"Shutdown before tier {tier_id}, stopping...")
        break
    tier_results[tier_id] = run_tier(tier_id)

# Save checkpoint in finally
try:
    ...
finally:
    if is_shutdown_requested() and checkpoint:
        checkpoint.status = "interrupted"
        save_checkpoint(checkpoint, checkpoint_path)
```

#### 4. Tier Progress Indicators for Parallel Workers

```python
from concurrent.futures import as_completed

total = len(tier_config.subtests)
start_time = time.time()
completed = 0

for future in as_completed(futures):
    subtest_id = futures[future]
    try:
        results[subtest_id] = future.result()
    except Exception as e:
        results[subtest_id] = create_error_result(subtest_id, e)
    finally:
        completed += 1
        elapsed = time.time() - start_time
        active = total - completed
        logger.info(
            f"[PROGRESS] Tier {tier_id}: {completed}/{total} complete, "
            f"{active} active, elapsed: {elapsed:.0f}s"
        )
```

#### 5. Suppress Expected-Failure Subprocess Logs

```python
# Add log_on_error kwarg to run_subprocess()
def run_subprocess(cmd, *, check=True, log_on_error=True, **kwargs):
    try:
        return subprocess.run(cmd, check=check, **kwargs)
    except subprocess.CalledProcessError as e:
        if log_on_error:
            logger.error(f"Command failed: {e.cmd!r} → exit {e.returncode}")
        raise

# Add log_errors kwarg to git_utils.run()
def run(cmd, *, check=True, log_errors=True, **kwargs):
    try:
        return subprocess.run([str(c) for c in cmd], check=check, **kwargs)
    except subprocess.CalledProcessError as e:
        if log_errors:
            logger.error(f"git command failed: {e.cmd!r} → exit {e.returncode}")
        raise

# At probe / first-try-cleanup call sites:
result = run(["git", "rev-parse", "--verify", branch], check=False, log_errors=False)
branch_exists = result.returncode == 0
```

#### 6. Add log_debug() to Bash Logging Library

```bash
# Colors for output: RED=error, GREEN=info, YELLOW=warn, BLUE=debug
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*" >&2; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_debug() { echo -e "${BLUE}[DEBUG]${NC} $*"; }
```

Verify: `bash -n <script>` + `pre-commit run --files <script>` (ShellCheck).

#### 7. Inline Terminal Status via Carriage Return

```python
import os

_last_was_inline: bool = False

def _term_width() -> int:
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80

def print_status(state: str, detail: str = "", inline: bool = False) -> None:
    global _last_was_inline
    line = f"[{state}]" + (f" {detail}" if detail else "")
    if inline:
        padding = max(0, _term_width() - len(line))
        print(f"\r{line}{' ' * padding}", end="", flush=True)
        _last_was_inline = True
    else:
        if _last_was_inline:
            print()
        print(line, flush=True)
        _last_was_inline = False

def clear_inline() -> None:
    global _last_was_inline
    if _last_was_inline:
        print()
        _last_was_inline = False

# Transient (overwrite): DISCONNECTED, RECONNECTING, retrying
# Permanent (newline): CONNECTED, RECONNECTED, actual events
```

#### 8. Extract Duplicate Logging Blocks into Helper

```python
# Pattern: void helper with mock-logger tests
def _log_checkpoint_resume(self, checkpoint_path: Path) -> None:
    """Log checkpoint resume status."""
    logger.info(f"Resuming from checkpoint: {checkpoint_path}")
    logger.info(f"Previously completed: {self.checkpoint.get_completed_run_count()} runs")

# Test pattern (void method — patch logger, assert calls)
with patch("module.path.logger") as mock_logger:
    obj._log_checkpoint_resume(path)
mock_logger.info.assert_has_calls([call("msg1"), call("msg2")])
assert mock_logger.info.call_count == 2
```

### Detailed Integration Notes

#### JSON Formatter: Key Design Points

- Use `record.getMessage()` (not `record.msg`) to resolve lazy `%s` formatting
- Build `_DEFAULT_ATTRS` snapshot at class level, include `{"message", "msg", "args"}` explicitly
- Prefix reserved-field collisions with `ctx_` to prevent silent data loss
- Use `default=str` in `json.dumps` for non-serializable values (datetimes, custom classes)
- Apply `JsonFormatter` to **all** handlers — set formatter before adding handlers or loop over them
- When `json_format=True`, the `format` string argument to `basicConfig` is effectively ignored

#### Subprocess Log Suppression: Safety Guarantee

`log_on_error=False` / `log_errors=False` only suppresses `logger.error()`. The `CalledProcessError` still propagates. Callers that do not catch it will still fail loudly.

#### Signal Handling: Worker Coordination

For multi-process workers, use `multiprocessing.Manager.Event()` to propagate shutdown across process boundaries:

```python
class RateLimitCoordinator:
    def __init__(self, manager):
        self._shutdown_event = manager.Event()

    def signal_shutdown(self):
        self._shutdown_event.set()

    def is_shutdown_requested(self):
        return self._shutdown_event.is_set()
```

Check shutdown **before** starting new work (tier, run, task), not mid-task.

#### Inline Status: Padding is Critical

Without padding to terminal width, shorter lines leave residue from longer previous lines. Always pad: `' ' * max(0, _term_width() - len(line))`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Use `python-json-logger` package | Considered adding as a dependency for JSON formatting | Unnecessary for a shared library; stdlib `json` + `logging.Formatter` does everything needed | Check if stdlib can do the job before adding a dependency — for JSON formatting it absolutely can |
| Access extra fields via `record.extra` | Assumed `LogRecord` exposes `.extra` attribute | `logging.LoggerAdapter.process()` sets extras as individual attributes via `setattr(record, key, value)` | Detect extras by diffing `record.__dict__` against a baseline snapshot of default `LogRecord` attrs |
| Use `record.msg` instead of `record.getMessage()` | `record.msg` is the raw format string; used it directly | Lazy `%s` args are not applied; output is the unformatted template | Always call `record.getMessage()` in custom formatters |
| Pass `format=` to `basicConfig` with custom formatter | Passed `format` kwarg alongside a custom handler formatter | The `format` kwarg can override handler formatters in some configurations | When using custom formatters, set them on handlers explicitly; omit `format` from `basicConfig` |
| Print every status on new line (terminal) | Each transient state (DISCONNECTED, RECONNECTING) used `print()` | Creates a wall of repeating status text when service is down — hundreds of lines | Transient states should overwrite in place; only permanent states deserve their own line |
| Suppress transient states entirely (terminal) | Skip printing DISCONNECTED/RECONNECTING, only show CONNECTED | Loses all visibility during reconnection; user sees nothing and thinks it is frozen | Transient states must be visible but should not accumulate; inline overwrite is the right balance |

## Results & Parameters

### JSON Log Output Format

```json
{"timestamp": "2026-03-25T10:00:00.123456+00:00", "level": "INFO", "logger": "myapp.svc", "message": "Request processed", "request_id": "abc-123", "duration_ms": 42}
```

### Stage Log Output Format

```
2026-01-04T19:30:15.234Z [T0_00] Stage: AGENT - Starting
2026-01-04T19:30:28.456Z [T0_00] Stage: AGENT - Complete (13.2s)
2026-01-04T19:30:35.890Z [T0_00] Stage: COMPLETE - All stages complete (20.7s)
```

### Progress Log Output Format

```
[PROGRESS] Tier T0: 1/24 complete, 23 active, elapsed: 15s
[PROGRESS] Tier T0: 24/24 complete, 0 active, elapsed: 320s
```

### Checkpoint Status Values

| Status | Meaning |
| -------- | --------- |
| `running` | Normal execution in progress |
| `paused_rate_limit` | Paused for rate limit |
| `interrupted` | User interrupted (Ctrl+C \| SIGTERM) |
| `completed` | Finished normally |
| `failed` | Error occurred |

### Subprocess Log Suppression: Files to Modify

| File | Change |
| ------ | -------- |
| `<project>/utils/helpers.py` | Add `log_on_error: bool = True` kwarg; guard `logger.error()` |
| `<project>/automation/git_utils.py` | Add `log_errors: bool = True` kwarg; guard `logger.error()` |
| Call sites (probe / first-try-cleanup) | Pass `log_on_error=False` or `log_errors=False` |

### Shell Log Level: Key Details

- Use `$*` (not `$1`) for variadic messages
- `log_error` writes to stderr (`>&2`); `log_debug` / `log_info` write to stdout
- Update the colors comment to document which color maps to which level

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Issue #45 - Structured JSON logging; PR #301 subprocess log suppression | PR #78 451 tests pass; PR #301 1403 tests pass |
| ProjectScylla | PR #139 stage logging; PR #140 progress indicators; PR #141 signal handling | All PRs merged to main |
| Odysseus | odysseus-console.py NATS event viewer inline status | Syntax checked; eliminates terminal spam during NATS downtime |
| ProjectHephaestus | Issue #781 / PR #829 - add log_debug() to docker_common.sh | ShellCheck + pre-commit passed; auto-merge |
| ProjectScylla | Issue #713 / PR #761 - extract duplicate checkpoint logging helper | 9 tests pass (4 pre-existing + 5 new) |
