---
name: debugging-loggeradapter-process-dict-mutation
description: "Fix LoggerAdapter.process() mutating caller's extra dict and add thread-safe context reads. Use when: (1) ContextLogger or LoggerAdapter subclass modifies kwargs in-place, (2) shared dicts leak context between log calls."
category: debugging
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - logging
  - thread-safety
  - dict-mutation
  - LoggerAdapter
  - ContextLogger
---

# LoggerAdapter.process() Dict Mutation Fix

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Fix `ContextLogger.process()` mutating caller-provided `extra` dict and add thread-safe `_context` reads |
| **Outcome** | Successful — all 15 tests pass, PR created |
| **Verification** | verified-local |
| **Project** | ProjectHephaestus |

## When to Use

- A `LoggerAdapter` subclass overrides `process()` and calls `extra.update()` on the caller's dict
- Context from one log call leaks into subsequent calls because the same `extra` dict is reused
- A logger's internal context dict is read without holding a lock while other methods (`bind`, `unbind`) acquire the lock before mutation
- Any `process()` override that modifies `kwargs["extra"]` in-place rather than creating a new dict

## Verified Workflow

### Quick Reference

```python
# BEFORE (buggy — mutates caller's dict):
def process(self, msg, kwargs):
    extra = kwargs.get("extra", {})
    extra.update(self._context)        # mutates caller's dict!
    kwargs["extra"] = extra
    return msg, kwargs

# AFTER (safe — creates new dict, acquires lock):
def process(self, msg, kwargs):
    with self._context_lock:
        context = self._context.copy()
    kwargs["extra"] = {**kwargs.get("extra", {}), **context}
    return msg, kwargs
```

### Detailed Steps

1. **Identify the mutation**: `extra.update(self._context)` modifies the dict object that the caller passed in via `kwargs["extra"]`. If the caller reuses that dict, context keys persist across calls.
2. **Fix with spread operator**: Replace `extra.update()` with `{**caller_extra, **context}` to create a fresh dict each time. Context keys from `self._context` override caller keys (intentional — logger context takes priority).
3. **Add lock for thread safety**: Wrap the `self._context` read in `with self._context_lock:` to prevent reading a partially-updated context if another thread is calling `bind()` or `unbind()` concurrently. Copy while holding the lock, then release before doing anything else.
4. **Write regression tests**:
   - Test that caller's `extra` dict is unchanged after `process()` is called
   - Test that context added via `bind()` appears in `process()` output
5. **Verify existing tests still pass**: Run the full logging test suite to confirm no regressions.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A — direct fix | The pattern was well-understood from the issue description | N/A | When the mutation pattern is `extra.update(self._context)`, the fix is always to create a new dict via spread. No need for `copy()` + `update()` intermediate step. |

## Results & Parameters

### Fix Pattern

```python
# Thread-safe, non-mutating process() for any LoggerAdapter subclass:
def process(self, msg: Any, kwargs: Any) -> tuple[Any, Any]:
    with self._context_lock:
        context = self._context.copy()
    kwargs["extra"] = {**kwargs.get("extra", {}), **context}
    return msg, kwargs
```

### Test Pattern

```python
def test_process_does_not_mutate_caller_extra(self) -> None:
    logger = get_logger("test.no_mutate", context={"ctx_key": "ctx_val"})
    caller_extra: dict[str, str] = {"request_id": "abc"}
    original_extra = caller_extra.copy()
    logger.process("msg", {"extra": caller_extra})
    assert caller_extra == original_extra

def test_process_includes_bound_context(self) -> None:
    base = get_logger("test.bound_context")
    bound = base.bind(user="alice", session="s1")
    _msg, kwargs = bound.process("hello", {})
    assert kwargs["extra"]["user"] == "alice"
    assert kwargs["extra"]["session"] == "s1"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #60 — ContextLogger.process mutation fix | 15/15 tests pass, PR #118 |
