---
name: logging-contextvars-ambient-state
description: "Use contextvars.ContextVar for ambient logging/tracing state (correlation IDs, trace IDs) instead of mutable globals or explicit parameters. Thread-safe and async-safe by design. Use when: propagating context across function call stacks, thread boundaries, and async contexts without explicitly threading it as a parameter."
category: architecture
date: 2026-05-28
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - contextvars
  - logging
  - correlation-id
  - trace-id
  - ambient-state
  - thread-safety
  - async-safety
---

# Logging: contextvars for Ambient State Propagation

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-28 |
| **Objective** | Propagate correlation IDs and trace IDs across function call stacks, threads, and async contexts without explicit parameters |
| **Outcome** | Successful propagation of GH_TRACE_ID to GitHub subprocess via ambient contextvars |
| **Verification** | verified-ci |

## When to Use

- Propagating correlation IDs (request tracking) across function call stacks
- Passing trace IDs or request context to subprocesses (via environment variables)
- Avoiding cluttering function signatures with "context" parameters
- Working with both sync and async code in the same codebase
- Ensuring thread-safety without locks or thread-local storage
- Subprocess spawned by application should inherit the ambient context (e.g., CI/CD trace ID)

## Verified Workflow

### Quick Reference

```python
import contextvars
import os

# 1. Define ContextVar at module level
_correlation_id_var = contextvars.ContextVar(
    'correlation_id',
    default=None
)

# 2. Accessor function to read current value
def get_current_correlation_id() -> str | None:
    """Get the current correlation ID from context.

    Returns:
        The correlation ID if set, None otherwise.
    """
    return _correlation_id_var.get()

# 3. Setter function to set value
def set_correlation_id(correlation_id: str | None) -> contextvars.Token:
    """Set the correlation ID in context.

    Args:
        correlation_id: The correlation ID to set.

    Returns:
        Token that can be used to reset context later.
    """
    return _correlation_id_var.set(correlation_id)

# 4. Context manager for scoped binding
def correlation_id_scope(correlation_id: str | None):
    """Context manager to temporarily set correlation ID.

    Usage:
        with correlation_id_scope("req-123"):
            # Inside this block, get_current_correlation_id() == "req-123"
            do_work()
        # After exiting, context is restored
    """
    from contextlib import contextmanager

    @contextmanager
    def _scope():
        token = set_correlation_id(correlation_id)
        try:
            yield
        finally:
            _correlation_id_var.reset(token)

    return _scope()

# 5. Use in subprocesses (inject into environment)
def run_subprocess(cmd: list[str]) -> str:
    """Run subprocess, injecting correlation ID into environment."""
    env = os.environ.copy()

    if cid := get_current_correlation_id():
        env['GH_TRACE_ID'] = cid

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    return result.stdout
```

### Detailed Steps

1. **Define ContextVar at module level** (typically in a logging utilities module):
   ```python
   import contextvars

   _correlation_id_var = contextvars.ContextVar('correlation_id', default=None)
   ```
   - Name is arbitrary (used for debugging)
   - `default=None` means reads return None before any set() call
   - Module-level definition ensures single instance across all code

2. **Create accessor function**:
   ```python
   def get_current_correlation_id() -> str | None:
       return _correlation_id_var.get()
   ```
   - Simple read: returns current value or default
   - No locks needed; thread-safe by design
   - Works in async contexts too

3. **Create setter function** that returns a Token:
   ```python
   def set_correlation_id(cid: str) -> contextvars.Token:
       return _correlation_id_var.set(cid)
   ```
   - Token can later reset the context to its previous value
   - Stores the old value internally

4. **Create context manager for scoped binding**:
   ```python
   @contextmanager
   def correlation_id_scope(cid: str):
       token = set_correlation_id(cid)
       try:
           yield
       finally:
           _correlation_id_var.reset(token)
   ```
   - Automatically restores old value when exiting
   - Exception-safe: finally block ensures reset happens

5. **Inject into subprocess environment**:
   ```python
   env = os.environ.copy()
   if cid := get_current_correlation_id():
       env['GH_TRACE_ID'] = cid
   subprocess.run(cmd, env=env)
   ```
   - Child process inherits the environment variable
   - Walrus operator: concise None-check and assignment

6. **Test isolation**: ContextVar values are automatically isolated per thread and async task
   ```python
   # Each thread/task has its own value
   # No cross-contamination between concurrent contexts
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Storing correlation ID in os.environ at module level, reading with os.environ.get() | Works for subprocess env propagation but affects the whole process; one test sets the env var and another test inherits it, causing cross-test contamination | os.environ is global and mutable; contextvars provide per-context isolation |
| 2 | Using thread-local storage (threading.local()) for correlation ID | Works for threads but not async; async tasks in the same thread share the same thread-local storage, so correlation IDs bleed between concurrent tasks | threading.local() does not work with asyncio; contextvars handle both threads and async tasks |
| 3 | Passing correlation ID as explicit parameter to every function: run_subprocess(cmd, cid=None) | Clutters signatures; functions that don't use the cid still need the parameter; call chains become verbose; refactoring is painful when adding a new layer | Ambient context via contextvars is transparent to intermediate functions; only the layers that need it read it |
| 4 | Storing contextvar in a dict: `_context = {}; _context['cid']` instead of using ContextVar | Manual dict management doesn't get thread/async isolation; requires explicit locking if concurrent access is possible | ContextVar is purpose-built for this: isolation is automatic, no locks needed |
| 5 | Using ContextVar but not providing a reset mechanism; just calling set() | After test 1 sets cid, test 2 sees cid from test 1 (same context) if tests run in same context | Always save the Token and reset it; use context managers to guarantee cleanup |
| 6 | Reading correlation ID at module import time instead of at call time | If set() is called after import, the module-level read gets None | Read at call time (inside functions), not at module level; set() is called at runtime by application entry points |

## Results & Parameters

### Correlation ID Context Setup (Copy-Paste Ready)

```python
# hephaestus/logging/utils.py

import contextvars
import os
from contextlib import contextmanager
from typing import Optional

_correlation_id_var = contextvars.ContextVar('correlation_id', default=None)

def get_current_correlation_id() -> Optional[str]:
    """Get the current correlation ID from context.

    Returns:
        The correlation ID if set, None otherwise.

    Example:
        >>> set_correlation_id("req-abc123")
        >>> get_current_correlation_id()
        'req-abc123'
    """
    return _correlation_id_var.get()

def set_correlation_id(correlation_id: Optional[str]) -> contextvars.Token:
    """Set the correlation ID in context.

    Args:
        correlation_id: The correlation ID to set (None to clear).

    Returns:
        Token that can be used to reset context later.

    Example:
        >>> token = set_correlation_id("req-xyz")
        >>> get_current_correlation_id()
        'req-xyz'
        >>> _correlation_id_var.reset(token)
        >>> get_current_correlation_id()
    """
    return _correlation_id_var.set(correlation_id)

@contextmanager
def correlation_id_scope(correlation_id: Optional[str]):
    """Context manager to temporarily set correlation ID.

    Automatically restores the previous value on exit.

    Args:
        correlation_id: The correlation ID to set.

    Yields:
        None.

    Example:
        >>> with correlation_id_scope("req-scope-123"):
        ...     print(get_current_correlation_id())  # "req-scope-123"
        >>> print(get_current_correlation_id())  # None (restored)
    """
    token = set_correlation_id(correlation_id)
    try:
        yield
    finally:
        _correlation_id_var.reset(token)
```

### Subprocess Injection Pattern

```python
# hephaestus/utils/helpers.py

import subprocess

def run_subprocess(cmd: list[str], **kwargs) -> str:
    """Run subprocess, injecting correlation ID into environment.

    Args:
        cmd: List of command arguments.
        **kwargs: Additional arguments to subprocess.run().

    Returns:
        stdout from the subprocess.

    Raises:
        subprocess.CalledProcessError: If subprocess returns non-zero.
    """
    env = kwargs.pop('env', None) or os.environ.copy()

    # Inject correlation ID into subprocess environment
    from hephaestus.logging.utils import get_current_correlation_id

    if cid := get_current_correlation_id():
        env['GH_TRACE_ID'] = cid

    result = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        **kwargs,
    )
    result.check_returncode()
    return result.stdout
```

### Test Case Isolation Example

```python
# tests/unit/logging/test_correlation_id_context.py

import pytest
from hephaestus.logging.utils import (
    get_current_correlation_id,
    set_correlation_id,
    correlation_id_scope,
)

def test_default_is_none():
    """ContextVar defaults to None."""
    assert get_current_correlation_id() is None

def test_set_and_get():
    """Setting correlation ID makes it readable."""
    token = set_correlation_id("req-123")
    assert get_current_correlation_id() == "req-123"
    # Clean up
    import contextvars
    _correlation_id_var.reset(token)

def test_context_manager_sets_and_restores():
    """Context manager scope automatically restores previous value."""
    set_correlation_id("outer")
    with correlation_id_scope("inner"):
        assert get_current_correlation_id() == "inner"
    assert get_current_correlation_id() == "outer"

def test_thread_isolation():
    """Each thread has isolated correlation ID."""
    import threading
    results = {}

    def thread_func(cid):
        set_correlation_id(cid)
        results[threading.current_thread().name] = get_current_correlation_id()

    set_correlation_id("main")
    t1 = threading.Thread(target=thread_func, args=("thread-1",), name="T1")
    t2 = threading.Thread(target=thread_func, args=("thread-2",), name="T2")
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Main thread was not affected by thread spawns
    assert get_current_correlation_id() == "main"
    # Each thread had its own value
    assert results["T1"] == "thread-1"
    assert results["T2"] == "thread-2"

def test_subprocess_receives_env_var():
    """Subprocess inherits correlation ID via environment."""
    import subprocess

    set_correlation_id("req-subprocess-test")

    env = os.environ.copy()
    if cid := get_current_correlation_id():
        env['GH_TRACE_ID'] = cid

    result = subprocess.run(
        ["sh", "-c", "echo $GH_TRACE_ID"],
        env=env,
        capture_output=True,
        text=True,
    )

    assert "req-subprocess-test" in result.stdout
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #633 — correlation_id propagation to gh subprocess | hephaestus/logging/utils.py:81-141, hephaestus/utils/helpers.py:170-172; 10 tests in test_correlation_id_context.py all passing |
