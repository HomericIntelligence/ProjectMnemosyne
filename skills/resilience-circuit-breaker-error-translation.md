---
name: resilience-circuit-breaker-error-translation
description: "Translate CircuitBreakerOpenError to domain exception at integration boundary to preserve caller exception semantics. Use when: wrapping low-level circuit breaker in a service-layer function where callers expect domain-specific exceptions."
category: architecture
date: 2026-05-28
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - circuit-breaker
  - error-handling
  - exception-translation
  - integration-boundary
  - resilience
---

# Resilience: CircuitBreaker Error Translation at Boundary

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-28 |
| **Objective** | Preserve caller exception semantics when wrapping low-level circuit breaker primitives by translating CircuitBreakerOpenError to domain exceptions |
| **Outcome** | Successful integration of circuit breaker into _gh_call() with zero breaking changes to existing error handling |
| **Verification** | verified-ci |

## When to Use

- Wrapping a low-level circuit breaker (e.g., pybreaker) in a service-layer function
- Callers expect domain-specific exceptions (e.g., GitHubUnavailableError) but the breaker raises CircuitBreakerOpenError
- You need to preserve exception handling chains for callers already catching domain exceptions
- Integration layer should be transparent: callers should not know the breaker exists

## Verified Workflow

### Quick Reference

```python
from pybreaker import CircuitBreaker, CircuitBreakerOpenError

# 1. Define domain exception
class GitHubUnavailableError(RuntimeError):
    """Raised when GitHub API is unavailable (circuit breaker open)."""
    pass

# 2. Create circuit breaker instance
_GH_BREAKER = CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
    listeners=[breaker_listener],  # optional: log state changes
)

# 3. Wrap the call and translate errors
def _gh_call(cmd, json_output=False, timeout_ms=None):
    """Execute GitHub CLI command with circuit breaker protection.

    Raises:
        CircuitBreakerOpenError → GitHubUnavailableError
        subprocess.CalledProcessError → re-raised unchanged
        GitHubUnavailableError: When GitHub API is unavailable
    """
    try:
        return _GH_BREAKER.call(
            _gh_subprocess_call,
            cmd=cmd,
            json_output=json_output,
            timeout_ms=timeout_ms,
        )
    except CircuitBreakerOpenError as exc:
        raise GitHubUnavailableError(
            f"GitHub API unavailable (circuit open, {_GH_BREAKER.fail_counter} recent failures)"
        ) from exc
```

### Detailed Steps

1. **Define domain exception** at module level (near other domain exceptions for this service):
   ```python
   class GitHubUnavailableError(RuntimeError):
       """Raised when GitHub API is unavailable."""
       pass
   ```
   - Inherit from a base exception callers already expect (RuntimeError, Exception, etc.)
   - Document the specific failure mode in the docstring

2. **Create circuit breaker instance** at module level (will be shared across all calls):
   ```python
   _GH_BREAKER = CircuitBreaker(
       fail_max=5,          # open after 5 consecutive failures
       reset_timeout=60,    # attempt recovery after 60s
       listeners=[...],     # optional: log state transitions
   )
   ```

3. **Wrap the low-level call** in a function that catches CircuitBreakerOpenError:
   ```python
   def _gh_call(...):
       try:
           return _GH_BREAKER.call(
               _gh_subprocess_call,
               cmd=cmd,
               ...
           )
       except CircuitBreakerOpenError as exc:
           raise GitHubUnavailableError(...) from exc
   ```

4. **Preserve the exception chain** with `raise ... from exc`:
   - Ensures `exc.__cause__` points to the original CircuitBreakerOpenError
   - Callers can access the root cause if needed: `except GitHubUnavailableError as e: e.__cause__`

5. **Do not catch subprocess.CalledProcessError** (or other service errors):
   - These should propagate unchanged — they are legitimate caller-level exceptions
   - Only translate the circuit breaker's own exceptions

6. **Test that existing error handling still works**:
   ```python
   # Callers that were catching RuntimeError continue to work:
   try:
       _gh_call([...])
   except RuntimeError:  # GitHubUnavailableError is a RuntimeError
       log_error("GitHub is down")

   # New code can catch the specific exception:
   try:
       _gh_call([...])
   except GitHubUnavailableError:
       log_error("GitHub circuit open")
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Wrapping breaker.call() without error translation; CircuitBreakerOpenError escaped to callers uncaught | Callers' existing exception handlers (`except RuntimeError`) did not catch CircuitBreakerOpenError — new internal exception type broke backward compatibility | Error translation at the boundary is essential: internal implementation details (circuit breaker library) must not leak into the caller's exception hierarchy |
| 2 | Raising a base Exception instead of a domain-specific class | Lost semantic information about WHY the error occurred; callers could not distinguish circuit-open from other failures | Domain exceptions preserve semantic meaning: GitHubUnavailableError tells callers exactly what went wrong, enabling targeted recovery strategies |
| 3 | Catching and swallowing CircuitBreakerOpenError, returning None instead of raising | Callers had no signal that GitHub was unavailable; retry logic never triggered because no exception was raised | Exceptions must propagate: returning None masks failures and prevents proper error handling in the call stack |
| 4 | Not including the original exception in the raise chain (`raise GitHubUnavailableError(...)` instead of `from exc`) | Debugging was difficult because the stack trace showed only the outer exception; the original CircuitBreakerOpenError context was lost | Always use `raise ... from exc` to preserve the full error context for debugging |

## Results & Parameters

### Circuit Breaker Configuration for GitHub API

```python
from pybreaker import CircuitBreaker

_GH_BREAKER = CircuitBreaker(
    fail_max=5,               # open after 5 consecutive command failures
    reset_timeout=60,         # allow recovery attempt after 60s
    name="GitHub CLI API",    # for logging
)

# Optional: add a listener to log state transitions
def breaker_listener(cb, before_call, call_args, call_kwargs, result, exception, *args, **kwargs):
    if exception:
        logger.warning(f"GitHub CLI call failed: {exception}")
    if cb.opened:
        logger.error(f"GitHub circuit breaker OPEN after {cb.fail_counter} failures")
    if cb.closed:
        logger.info(f"GitHub circuit breaker CLOSED, resumed normal operation")

_GH_BREAKER.listeners.append(breaker_listener)
```

### Exception Translation Pattern (Copy-Paste Ready)

```python
from pybreaker import CircuitBreakerOpenError

class GitHubUnavailableError(RuntimeError):
    """Raised when GitHub API is unavailable due to circuit breaker or service issues."""
    pass

def _gh_call(cmd, json_output=False, timeout_ms=None):
    """Execute GitHub CLI command with circuit breaker protection.

    Args:
        cmd: List of CLI arguments (e.g., ["pr", "view", "123"])
        json_output: If True, parse response as JSON
        timeout_ms: Optional timeout in milliseconds

    Returns:
        Command output (str) or parsed JSON (dict/list)

    Raises:
        GitHubUnavailableError: When GitHub API is unavailable
        subprocess.CalledProcessError: When command returns non-zero
        Exception: Other subprocess errors
    """
    try:
        return _GH_BREAKER.call(
            _gh_subprocess_call,
            cmd=cmd,
            json_output=json_output,
            timeout_ms=timeout_ms,
        )
    except CircuitBreakerOpenError as exc:
        raise GitHubUnavailableError(
            f"GitHub API unavailable (circuit open after {_GH_BREAKER.fail_counter} failures, "
            f"retry after {_GH_BREAKER.reset_timeout}s)"
        ) from exc
```

### Caller Code (No Changes Required)

```python
# Old code that catches RuntimeError continues to work:
try:
    result = _gh_call(["pr", "view", "123", "--json=state"])
except RuntimeError as e:
    logger.error(f"GitHub command failed: {e}")
    # Handles both subprocess errors and circuit breaker errors uniformly

# New code can catch the specific exception:
try:
    result = _gh_call(["pr", "view", "123", "--json=state"])
except GitHubUnavailableError:
    logger.error("GitHub is unavailable, circuit breaker open")
    # Trigger backup strategy (retry later, use cached data, etc.)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #633 — CircuitBreaker integration for _gh_call | hephaestus/automation/github_api.py:399-414; CI passed with 5 new circuit breaker tests |
