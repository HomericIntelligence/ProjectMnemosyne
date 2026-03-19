---
name: e2e-runner-hang-signal-fixes
description: "Fix E2E experiment runner hanging and ignoring Ctrl+C/Ctrl+Z signals during parallel execution. Use when: manage_experiment.py hangs, signals are ignored, or SIGTSTP does graceful shutdown instead of force kill."
category: debugging
date: 2026-03-18
user-invocable: false
---

# E2E Runner Hang and Signal Handling Fixes

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-18 |
| Branch | `fix-experiment-hang-signal-handling` |
| Objective | Fix experiment runner hanging after tier initialization and not responding to Ctrl+C or Ctrl+Z |
| Outcome | SUCCESS — 4924 tests pass, 77.74% coverage. All 6 hang/signal bugs fixed with 14 new guard tests |
| PR | #1515 |

## When to Use

- `manage_experiment.py run` hangs after printing "Starting N tiers in parallel" messages
- Ctrl+C has no effect during long-running parallel tier or subtest execution
- Ctrl+Z does graceful shutdown instead of force-killing the process group
- `future.result()` blocks indefinitely inside `as_completed()` loops
- `proc.communicate(timeout=3600)` blocks for the full timeout even after shutdown is requested
- Worker threads hang forever in `_resume_event.wait()` after main thread crashes
- Rate limit sleep loop (`time.sleep()`) ignores shutdown requests between iterations

**Trigger signals**:
- Process hangs at "ParallelismScheduler initialized" / "Starting N tiers in parallel"
- `is_shutdown_requested()` returns True but execution continues
- `_kill_group` handler for SIGTSTP is overwritten by `terminal_guard()`

## Verified Workflow

### Quick Reference

The core pattern is replacing blocking `as_completed()` + `future.result()` with `concurrent.futures.wait(timeout=2.0)` polling that checks `is_shutdown_requested()` between iterations:

```python
from concurrent.futures import FIRST_COMPLETED, wait

pending = set(futures.keys())
while pending:
    if is_shutdown_requested():
        for f in pending:
            f.cancel()
        raise ShutdownInterruptedError("Shutdown during parallel execution")
    done, pending = wait(pending, timeout=2.0, return_when=FIRST_COMPLETED)
    for future in done:
        result = future.result(timeout=0)  # Already done, no block
        # ... process result ...
```

### Bug 1: Replace `as_completed()` + `future.result()` (3 sites)

**Files**: `parallel_tier_runner.py`, `parallel_executor.py`, `manage_experiment.py`

The `as_completed(futures)` iterator yields futures as they complete, but `future.result()` blocks indefinitely if no future completes. The main thread never checks `is_shutdown_requested()`.

**Fix**: Replace with `wait(pending, timeout=2.0, return_when=FIRST_COMPLETED)` loop. On timeout (no future completed in 2s), loop back to shutdown check. Use `future.result(timeout=0)` on done futures (already complete, no blocking).

**Import change**: `from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait` (remove `as_completed`).

### Bug 2: Replace `proc.communicate(timeout=3600)` with polling

**File**: `stages.py` — `stage_execute_agent()`

Extract a helper function to reduce cyclomatic complexity:

```python
def _communicate_with_shutdown_check(
    proc: subprocess.Popen[str], timeout: float, ctx: RunContext,
) -> tuple[str, str]:
    poll_interval = 2.0
    remaining = float(timeout)
    while True:
        try:
            return proc.communicate(timeout=poll_interval)
        except subprocess.TimeoutExpired:
            remaining -= poll_interval
            if remaining <= 0:
                raise
            if is_shutdown_requested():
                _kill_process_group(proc)
                raise ShutdownInterruptedError(...) from None
```

**Key insight**: `communicate(timeout=N)` does NOT consume partial output on `TimeoutExpired` — the buffers remain attached to the pipe. Calling it in a loop is safe; the successful call returns all accumulated output.

### Bug 3: Add `stdin=subprocess.DEVNULL` to Popen

**File**: `stages.py:550`

One-line change. Without it, the agent subprocess inherits parent stdin and can hang on interactive prompts.

### Bug 4: Add shutdown check in rate limit sleep loop

**File**: `rate_limit.py:300-304`

Add `is_shutdown_requested()` check after each `time.sleep()` iteration. Restore checkpoint to "running" status before raising `ShutdownInterruptedError`.

### Bug 5: Add timeout to `_resume_event.wait()`

**File**: `parallel_executor.py:100`

Replace `self._resume_event.wait()` (blocks forever) with:
```python
while not self._resume_event.wait(timeout=2.0):
    if self._shutdown_event.is_set():
        return True  # Was paused, exiting due to shutdown
```

Uses the coordinator's own `_shutdown_event` (no import from `runner.py`).

### Bug 6: Fix SIGTSTP handler conflict

**File**: `terminal.py:74-76`

Remove SIGTSTP registration from `install_signal_handlers()`. The caller (`cmd_run`) registers its own `_kill_group` handler for SIGTSTP at line 889, but `terminal_guard()` at line 1173 overwrites it with the graceful handler. SIGTSTP is a job-control signal; callers should decide how to handle it.

### Improvement: Structured logging with thread-local context

**New file**: `log_context.py`

Uses `threading.local()` + `logging.Filter` to inject `tier_id`, `subtest_id`, and `run_num` into every log record. Format: `%(asctime)s [%(levelname)s] [T:%(thread)d] [%(tier_id)s/%(subtest_id)s/%(run_num)s] %(name)s: %(message)s`

Call `set_log_context(tier_id=..., subtest_id=..., run_num=...)` at worker entry points.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Named constant `_AGENT_POLL_INTERVAL` inside function | Used uppercase naming for module-level constants inside a function body | Ruff N806: variable in function should be lowercase | Extract to helper function or use lowercase variable name |
| `for f in pending: f.cancel()` in batch loop | Variable `f` reused from earlier `with open(summary_path) as f:` in same function scope | Mypy type error: `Future` incompatible with `TextIOWrapper` | Use unique variable names (`pending_future`) to avoid scope collisions |
| `type: ignore[attr-defined]` on LogRecord attributes | Added suppression comments to `record.tier_id = ...` | Mypy says the comments are unused — LogRecord accepts arbitrary attrs | Don't add preemptive type: ignore; let mypy tell you if it's needed |
| Single `communicate(timeout=full)` with post-check | Checked `is_shutdown_requested()` only after `communicate()` returns | Main thread blocked for up to 3600s; shutdown check never reached | Must poll with short timeouts to create shutdown check windows |
| SIGTSTP in `install_signal_handlers()` | Registered graceful handler for Ctrl+Z alongside Ctrl+C | Overwrites `cmd_run`'s `_kill_group` force-kill handler registered earlier | SIGTSTP is job-control, not interrupt — don't touch it in generic signal installer |

## Results & Parameters

| Metric | Value |
|--------|-------|
| Tests | 4924 passed (2 skipped) |
| Coverage | 77.74% |
| New tests | 14 (guard tests for all 6 bugs + logging) |
| Files modified | 7 source + 1 new + 6 test files |
| Poll interval | 2.0 seconds (balances responsiveness vs overhead) |
| Signal response time | < 4 seconds (2s poll + processing) |

### Key Parameters
```yaml
poll_interval: 2.0       # seconds between shutdown checks
wait_return_when: FIRST_COMPLETED  # concurrent.futures.wait strategy
future_result_timeout: 0  # done futures only, never blocks
resume_event_timeout: 2.0  # worker pause poll interval
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1515 — Fix hang and signal handling | [notes.md](../../references/notes.md) |

## Key Invariants

1. **`as_completed()` + `future.result()` blocks indefinitely** when no future completes — always use `wait(timeout=N)` instead.
2. **`communicate(timeout=N)` does NOT consume partial output** on TimeoutExpired — safe to call in a polling loop.
3. **Signal handlers set flags but cannot interrupt blocking calls** — the blocked thread must periodically check the flag.
4. **SIGTSTP is a job-control signal** with different semantics than SIGINT/SIGTERM — don't register it alongside graceful shutdown handlers.
5. **`threading.Event.wait()` without timeout blocks forever** — always add a timeout for interruptibility.
6. **`from None` in `raise X from None`** suppresses the `TimeoutExpired` exception chain in shutdown paths.
