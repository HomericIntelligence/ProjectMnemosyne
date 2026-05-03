---
name: testing-pytest-asyncio-event-mock-hang
description: "Fix pytest tests that hang when a coroutine internally reassigns a global asyncio.Event and then awaits it — pre-setting the module variable is ineffective because the coroutine overwrites it. Fix by patching the asyncio.Event constructor in the module's namespace so the coroutine receives a pre-set event. Use when: (1) coroutine does global _shutdown_event = asyncio.Event() internally, (2) pre-setting the module-level event before calling run() has no effect, (3) test hangs at _shutdown_event.wait() even though you set it beforehand."
category: testing
date: 2026-05-03
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - asyncio
  - pytest
  - asyncio.Event
  - hang
  - mock
  - patch
  - global
  - shutdown-event
  - coroutine
  - python
---

# Pytest asyncio.Event Constructor Patch — Fix Global Event Reassignment Hang

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-03 |
| **Objective** | Fix test that hung indefinitely because `run()` reassigned the global `_shutdown_event` with a new unset `asyncio.Event()`, discarding the pre-set test fixture |
| **Outcome** | SUCCESS — fix pushed to CI; CI was queued at session end (not yet confirmed green) |
| **Verification** | verified-local |

## When to Use

- A coroutine under test creates `asyncio.Event()` internally (e.g., `global _shutdown_event; _shutdown_event = asyncio.Event()`) and then calls `await _shutdown_event.wait()`
- Pre-setting `module._shutdown_event` before calling the coroutine has **no effect** — the coroutine overwrites it with a fresh unset event immediately
- Test hangs indefinitely (or until CI timeout) at the `_shutdown_event.wait()` call
- Stack trace from a timed-out run shows `epoll.poll(timeout=-1)` inside `asyncio._selector_events._SelectorEventLoop._run_once`
- CI logs show the daemon started (log message emitted) but never returned

## Verified Workflow

### Quick Reference

```python
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

def _make_run_mocks():
    mock_event = asyncio.Event()
    mock_event.set()  # Pre-set so wait() returns immediately
    return mock_event

async def test_run_returns_zero(self) -> None:
    settings = Settings(shutdown_timeout=0.1)
    mock_event = _make_run_mocks()

    # Patch asyncio.Event in the module's namespace, NOT the pre-existing variable
    with patch("keystone.daemon.asyncio.Event", return_value=mock_event):
        result = await keystone.daemon.run(settings)

    assert result == 0
```

### Detailed Steps

1. **Identify the reassignment pattern** inside the coroutine:
   ```python
   # Inside run():
   global _shutdown_event
   _shutdown_event = asyncio.Event()   # <-- NEW unset event every call
   ...
   await _shutdown_event.wait()        # <-- hangs forever in test context
   ```

2. **Understand why pre-setting the module variable fails**:
   ```python
   # This does NOT work — run() overwrites it:
   keystone.daemon._shutdown_event = asyncio.Event()
   keystone.daemon._shutdown_event.set()
   result = await keystone.daemon.run(settings)  # Still hangs!
   ```

3. **Create a pre-set event to inject**:
   ```python
   mock_event = asyncio.Event()
   mock_event.set()  # set() before run() is called
   ```

4. **Patch the constructor in the module's namespace** (not the variable):
   ```python
   # The patch intercepts the asyncio.Event() call INSIDE run()
   with patch("keystone.daemon.asyncio.Event", return_value=mock_event):
       result = await keystone.daemon.run(settings)
   ```
   The key is to patch `<module>.asyncio.Event` — the constructor as seen from the
   module's imported `asyncio` reference — not `asyncio.Event` globally.

5. **Combine with other mocks** for a complete daemon `run()` test:
   ```python
   def _make_run_mocks():
       mock_listener = MagicMock(spec=NATSListener)
       mock_listener.stop = AsyncMock()
       mock_claimer = MagicMock(spec=TaskClaimer)
       mock_claimer.drain = AsyncMock(return_value=True)
       mock_event_loop = MagicMock()
       mock_event_loop.add_signal_handler = MagicMock()
       mock_event = asyncio.Event()
       mock_event.set()
       return mock_listener, mock_claimer, mock_event_loop, mock_event

   async def test_run_returns_zero(self) -> None:
       settings = Settings(shutdown_timeout=0.1)
       mock_listener, mock_claimer, mock_event_loop, mock_event = _make_run_mocks()

       with patch("keystone.daemon.NATSListener", return_value=mock_listener):
           with patch("keystone.daemon.TaskClaimer", return_value=mock_claimer):
               with patch("asyncio.get_running_loop", return_value=mock_event_loop):
                   with patch("keystone.daemon.asyncio.Event", return_value=mock_event):
                       result = await keystone.daemon.run(settings)

       assert result == 0
   ```

6. **Run locally to verify**:
   ```bash
   pytest tests/test_daemon.py -v --timeout=30
   # Should complete in seconds, not hang
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Pre-set module-level event variable | `keystone.daemon._shutdown_event = asyncio.Event(); keystone.daemon._shutdown_event.set()` before calling `run()` | `run()` immediately overwrites the variable with `_shutdown_event = asyncio.Event()`, creating a new unset event; the pre-set value is discarded | Setting a module variable before calling a coroutine that reassigns that variable is a no-op — the coroutine always wins |
| `asyncio.create_task` concurrent setter | Spawned `asyncio.create_task(set_event())` to set the event concurrently after `run()` started | CodeQL flags this as a no-effect await; also fragile due to event loop scheduling order — no guarantee the task runs before `wait()` is reached | Concurrent task injection is unreliable and flags static analysis; constructor patching is safer and deterministic |

## Results & Parameters

```python
# Full working pattern for testing a daemon coroutine with internal asyncio.Event reassignment

import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock, patch

import keystone.daemon
from keystone.daemon import run
from keystone.settings import Settings
from keystone.nats_listener import NATSListener
from keystone.task_claimer import TaskClaimer


def _make_run_mocks():
    mock_listener = MagicMock(spec=NATSListener)
    mock_listener.stop = AsyncMock()
    mock_claimer = MagicMock(spec=TaskClaimer)
    mock_claimer.drain = AsyncMock(return_value=True)
    mock_event_loop = MagicMock()
    mock_event_loop.add_signal_handler = MagicMock()
    # Pre-set event: run() calls asyncio.Event() internally; patch it to return
    # an already-set event so _shutdown_event.wait() returns immediately.
    mock_event = asyncio.Event()
    mock_event.set()
    return mock_listener, mock_claimer, mock_event_loop, mock_event


class TestRun:
    async def test_run_returns_zero(self) -> None:
        settings = Settings(shutdown_timeout=0.1)
        mock_listener, mock_claimer, mock_event_loop, mock_event = _make_run_mocks()

        with patch("keystone.daemon.NATSListener", return_value=mock_listener):
            with patch("keystone.daemon.TaskClaimer", return_value=mock_claimer):
                with patch("asyncio.get_running_loop", return_value=mock_event_loop):
                    with patch("keystone.daemon.asyncio.Event", return_value=mock_event):
                        result = await keystone.daemon.run(settings)

        assert result == 0
```

### Diagnosis — Reading a Hung CI Stack Trace

When a test hangs and you use `--timeout-method=thread` (see companion skill), the stack trace will show:

```
  File ".../asyncio/_selector_events.py", line NNN, in _run_once
    event_list = self._selector.select(timeout)
  File ".../selectors.py", line NNN, in select
    fd_event_list = self._selector.poll(timeout, max_ev)
```

This confirms the event loop is stuck in `epoll.poll(timeout=-1)` — no tasks are ready.
The `timeout=-1` means it is waiting forever, which is the signature of an unset `asyncio.Event`.

Check CI logs for the last log message before the hang — if the daemon's startup message
was logged but `run()` never returned, the hang is inside `run()` at `await _shutdown_event.wait()`.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectKeystone | PR #535 (`243-auto-impl-test`), PR #541 (`fix/markdownlint-line-length`) | Fix pushed, CI queued at session end — not yet confirmed green |
