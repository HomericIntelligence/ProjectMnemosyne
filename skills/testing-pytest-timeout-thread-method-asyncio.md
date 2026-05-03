---
name: testing-pytest-timeout-thread-method-asyncio
description: "Fix pytest tests that hang indefinitely (CI job timeout) when using pytest-timeout with asyncio tests blocked in epoll.poll(-1). Use when: (1) async tests hang for exactly the CI job timeout with no output, (2) pytest-timeout fires but fails to interrupt the test, (3) asyncio event loop is blocked in _SelectorEventLoop._run_once → epoll.poll(-1) with no events ready."
category: testing
date: 2026-05-03
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - pytest
  - pytest-timeout
  - asyncio
  - epoll
  - signal
  - thread
  - timeout-method
  - event-loop
  - hang
  - ci
  - python
---

# Pytest-Timeout Thread Method for Asyncio Epoll Hangs

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-03 |
| **Objective** | Fix async tests that hang for the full CI job timeout when pytest-timeout's default signal method cannot interrupt epoll.poll(-1) |
| **Outcome** | SUCCESS — `--timeout-method=thread` successfully interrupts the asyncio event loop blocked in epoll; stack trace confirmed |
| **Verification** | verified-local (CI run was queued at session end; stack trace confirmed via log analysis) |
| **Project** | HomericIntelligence/ProjectKeystone PRs #535, #541 |

## When to Use

- pytest CI step runs for exactly the CI job timeout (e.g., 10 minutes) with **no test output** — this is the hang signature
- Tests use `asyncio_mode = "auto"` (pytest-asyncio) and call async code that awaits an event that never fires
- Stack trace (when available) shows: `_selector_events._SelectorEventLoop._run_once` → `_selector.poll(timeout)` → `epoll.poll(-1)` at the bottom
- `pytest-timeout` is installed but using default `--timeout-method=signal` — the timeout fires but does not interrupt the test
- The SIGALRM signal is delivered to the Python signal handler only when the blocked syscall returns — which never happens for `epoll.poll(-1)` with no events

## Verified Workflow

### Quick Reference

```toml
# pyproject.toml — add both settings together
[tool.pytest.ini_options]
addopts = "--timeout=30 --timeout-method=thread"

# Also add pytest-timeout to dev dependencies
[project.optional-dependencies]
dev = [
    "pytest-timeout>=2.3,<3",
]
```

### Detailed Steps

1. **Confirm the symptom**: The CI job runs for exactly the job-level timeout (e.g., `timeout-minutes: 10`) with no test failure output. This is a hang, not a test failure.

2. **Install pytest-timeout** in dev dependencies:
   ```toml
   [project.optional-dependencies]
   dev = [
       "pytest-timeout>=2.3,<3",
   ]
   ```

3. **Add `--timeout` and `--timeout-method=thread`** to `pytest.ini_options` in `pyproject.toml`:
   ```toml
   [tool.pytest.ini_options]
   addopts = "--cov=src/mypackage --cov-report=term-missing --cov-report=xml --timeout=30 --timeout-method=thread"
   ```
   The two flags **must be set together** — adding `--timeout=30` alone still uses the signal method by default.

4. **Why `thread` works**: The thread method spawns a watchdog thread that calls `thread.interrupt_main()` after the timeout. This delivers a `KeyboardInterrupt` into the main thread even while it is blocked in a C-level syscall (`epoll.poll(-1)`). The signal method (SIGALRM) only delivers when the blocked syscall returns, which never happens when there are no file descriptor events.

5. **Verify the fix locally**:
   ```bash
   pytest tests/ -v --timeout=30 --timeout-method=thread
   # Should see "TIMEOUT" output within 30s instead of hanging for 10 min
   ```

6. **Read the timeout stack trace** — when `--timeout-method=thread` fires on a hanging asyncio test, the stack trace confirms the root cause:
   ```
   event_list = self._selector.select(timeout)
   fd_event_list = self._selector.poll(timeout, max_ev)
   ```
   This confirms the asyncio event loop was blocked in epoll. The underlying test fix (patching `asyncio.Event` or the daemon's `_shutdown_event`) is a separate issue — see skill `testing-pytest-asyncio-daemon-coroutine-patch`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Default `--timeout-method=signal` | pytest-timeout with `--timeout=30` only, relying on default SIGALRM method | SIGALRM is delivered to Python signal handler only when the C-level `epoll.poll(-1)` syscall returns — which never happens with no events ready | Signal-based timeouts cannot interrupt blocking C-level syscalls; use thread method for asyncio tests |
| `--timeout=30` without `--timeout-method` | Added `addopts = "--timeout=30"` to pyproject.toml | Adds timeout but defaults to signal method; same hang occurs — CI still times out at job level | Both flags required: `--timeout=30 --timeout-method=thread` |

## Results & Parameters

### Configuration

```toml
# pyproject.toml — complete pytest section example
[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = "--cov=src/keystone --cov-report=term-missing --cov-report=xml --timeout=30 --timeout-method=thread"
testpaths = ["tests"]

[project.optional-dependencies]
dev = [
    "pytest>=8.3,<9",
    "pytest-asyncio>=0.24,<1",
    "pytest-cov>=6.0,<7",
    "pytest-timeout>=2.3,<3",
]
```

### Diagnostic Stack Trace (confirms epoll hang)

When `--timeout-method=thread` fires on a blocked asyncio test, the stack bottom looks like:

```
  File ".../asyncio/selector_events.py", line NNN, in _run_once
    event_list = self._selector.select(timeout)
  File ".../selectors.py", line NNN, in select
    fd_event_list = self._selector.poll(timeout, max_ev)
```

This is the definitive confirmation that `epoll.poll(-1)` is the blocking point.

### Timeout Value Guidelines

| Scenario | Recommended `--timeout` |
|----------|------------------------|
| Unit tests only | 10–30 seconds |
| Integration tests with I/O | 30–60 seconds |
| Tests involving network calls | 60–120 seconds |
| Full daemon startup tests | 30 seconds (with coroutine patching) |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectKeystone | PRs #535 (`243-auto-impl-test`) and #541 (`fix/markdownlint-line-length`) | `TestRunAsync` tests hung in `await keystone.daemon.run(settings)`; `--timeout-method=thread` revealed epoll stack trace |
