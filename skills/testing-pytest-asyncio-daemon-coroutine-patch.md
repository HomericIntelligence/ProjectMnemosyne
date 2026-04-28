---
name: testing-pytest-asyncio-daemon-coroutine-patch
description: "Fix pytest tests that hang indefinitely (CI timeout) when testing an async daemon by patching the coroutine function itself with AsyncMock instead of patching internal functions the coroutine calls. Use when: (1) pytest CI step times out (10-min limit) but individual tests do not fail, (2) daemon tests call main() which internally calls asyncio.run(coroutine()) that waits on a never-set Event, (3) patching run_routing_loop or other internal helpers is a no-op because main() does not call them directly."
category: testing
date: 2026-04-26
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - asyncio
  - pytest
  - daemon
  - AsyncMock
  - coroutine
  - patch
  - hang
  - timeout
  - event-loop
  - python
---

# Pytest Async Daemon Coroutine Patch — Stop Event-Loop Hangs

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-26 |
| **Objective** | Fix 9 daemon tests that caused CI to timeout (10 min) by hanging in a never-completing asyncio event loop |
| **Outcome** | SUCCESS — 200 tests in 1.26 s locally; CI went from 10-min timeout failure to green |
| **Verification** | verified-ci |
| **Project** | ProjectKeystone PR #451 (`fix/security-scan-gitleaks-jq`) |

## When to Use

- pytest CI step **times out** (e.g., `timeout-minutes: 10`) without reporting a test failure — this is the signature of hanging tests, not failing ones
- Tests call `main()` (or similar entry point) which internally calls `asyncio.run(run(settings))`
- `run()` is an `async def` that blocks on `await _shutdown_event.wait()` where nothing sets the event in test context
- The patch targets a function that `main()` does **not** call directly (e.g., `run_routing_loop`) — making the patch a silent no-op
- Tests assert log output that is emitted by `main()` itself (before the coroutine runs) — these are safe to keep
- Tests assert log output that is emitted **inside** the mocked coroutine — these must be removed or moved to `run()` unit tests

## Verified Workflow

### Quick Reference

```python
# CORRECT: patch the coroutine function itself
from unittest.mock import AsyncMock, patch

@patch("mymodule.daemon.run", new_callable=AsyncMock, return_value=0)
def test_main_starts(mock_run, caplog):
    with caplog.at_level(logging.INFO):
        result = main(["--log-level", "INFO"])
    assert result == 0
    mock_run.assert_called_once()

# For signal.signal assertions — use assert_any_call, not assert_called_once_with
# asyncio.runners.Runner internally calls signal.signal(SIGINT, ...) during asyncio.run()
mock_signal.assert_any_call(signal.SIGTERM, ANY)
```

### Detailed Steps

1. **Identify the actual call chain** from `main()` to find what is actually invoked:
   ```python
   # Check the real code — does main() call run_routing_loop? Or asyncio.run(run(...))?
   return asyncio.run(run(settings))   # run() is the coroutine to patch
   ```

2. **Replace patches of internal helpers with a patch of the coroutine function**:
   ```python
   # BEFORE (no-op — main() never calls run_routing_loop):
   @patch("mymodule.daemon.run_routing_loop", return_value=None)

   # BEFORE (prevents hang but skips all logging inside run()):
   @patch("mymodule.daemon.asyncio.run", return_value=0)

   # AFTER (correct — asyncio.run() still executes but receives the fast AsyncMock):
   @patch("mymodule.daemon.run", new_callable=AsyncMock, return_value=0)
   ```

3. **Audit log assertions** — determine which frame emits each log message:
   - Logs from `main()` itself (before `asyncio.run()`): safe to keep
   - Logs from inside `run()` (e.g., `finally` block of the coroutine): remove from `main()` tests; add to `run()` unit tests instead

4. **Fix `assert_called_once_with` on `signal.signal`**:
   - `asyncio.runners.Runner` internally registers a SIGINT handler during `asyncio.run()`
   - This makes the call count 2, not 1, causing `assert_called_once_with` to fail
   - Switch to `assert_any_call(signal.SIGTERM, ANY)`

5. **Delete dead tests** that assert behavior of functions `main()` never calls:
   - A test for `--poll-interval` being forwarded to `run_routing_loop` is dead code if `main()` does not call `run_routing_loop`
   - A test asserting `daemon_stopped` log from `main()` is dead if that log fires inside `run()`'s `finally` block

6. **Run locally to verify**:
   ```bash
   pytest tests/test_daemon.py -v --timeout=30
   # Should complete in seconds, not minutes
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Patch `run_routing_loop` | `@patch("keystone.daemon.run_routing_loop", return_value=None)` | `main()` never calls `run_routing_loop`; patch is a complete no-op; real coroutine still runs and hangs | Always trace the actual call chain from entry point before choosing a patch target |
| Patch `asyncio.run` | `@patch("keystone.daemon.asyncio.run", return_value=0)` | Prevents hang, but coroutine body never runs; tests that assert log output emitted inside `run()` silently fail | Patching `asyncio.run` skips the entire coroutine — only safe if no assertions depend on coroutine-internal side effects |
| `assert_called_once_with(signal.SIGTERM, ...)` | Exact-count assertion on `signal.signal` mock | `asyncio.runners.Runner` calls `signal.signal(SIGINT, ...)` internally during `asyncio.run()`, making total call count 2 | Use `assert_any_call` instead of `assert_called_once_with` for signal handlers when `asyncio.run()` is involved |

## Results & Parameters

```python
# Full working pattern for an async daemon test class

import signal
import logging
from unittest.mock import AsyncMock, patch, ANY
import pytest

class TestMain:
    @patch("keystone.daemon.run", new_callable=AsyncMock, return_value=0)
    def test_main_returns_zero_on_success(self, mock_run, caplog):
        with caplog.at_level(logging.INFO):
            result = main(["--log-level", "INFO"])
        assert result == 0
        mock_run.assert_called_once()

    @patch("keystone.daemon.signal.signal")
    @patch("keystone.daemon.run", new_callable=AsyncMock, return_value=0)
    def test_main_registers_sigterm(self, mock_run, mock_signal):
        main(["--log-level", "INFO"])
        # Must use assert_any_call: asyncio.run() also calls signal.signal for SIGINT
        mock_signal.assert_any_call(signal.SIGTERM, ANY)

    @patch("keystone.daemon.run", new_callable=AsyncMock, return_value=1)
    def test_main_propagates_nonzero_exit(self, mock_run):
        result = main(["--log-level", "INFO"])
        assert result == 1

# Tests that must be DELETED (or moved to run() unit tests):
# - test_main_accepts_poll_interval_arg  (tests forwarding to run_routing_loop — dead code)
# - test_main_logs_daemon_stopped         (daemon_stopped fires inside run() finally, not in main())
```

### CI Behavior Before / After

| Metric | Before Fix | After Fix |
|--------|-----------|-----------|
| CI outcome | FAILURE (timeout at 10 min) | PASS |
| Orphan process visible in logs | Yes — pytest process stuck | No |
| Test duration | >10 min (killed) | ~1.26 s for 200 tests |
| Failure mode | Timeout, not assertion error | N/A |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectKeystone | PR #451 `fix/security-scan-gitleaks-jq` | 9 hanging daemon tests fixed; CI confirmed green |
