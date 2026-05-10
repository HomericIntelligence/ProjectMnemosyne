---
name: refactor-context-manager-double-counter-stale-caller
description: "Detects and fixes double-increment bugs caused by incomplete context-manager
  refactors where callers still hold stale manual counter management code. Use when:
  (1) tests asserting counter == 1 observe 2 instead, (2) a context manager was introduced
  to own resource lifecycle but tests regressed, (3) a refactor moved try/finally lifecycle
  code into a context manager without auditing callers."
category: debugging
date: 2026-05-09
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: []
---

# Refactor: Context-Manager Double-Counter from Stale Caller

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-09 |
| **Objective** | Diagnose and fix double-increment of a counter after introducing a context manager that owns the lifecycle |
| **Outcome** | Test `test_inflight_increments_during_publish` regressed (`[2]` instead of `[1]`); fixed by removing stale manual counter management in caller |
| **Verification** | verified-ci |
| **Found In** | HomericIntelligence/ProjectHermes PR #522 |

## When to Use

- A test asserting `counter == 1` (or checking a list contains `[1]`) now observes `2` after a refactor
- A context manager was introduced to wrap a resource lifecycle (counters, semaphores, file handles)
- The refactored callee uses `with self._some_context():` but tests began failing immediately after merge
- Code review shows both a `with _ctx():` call AND a manual `counter += 1` / `counter -= 1` in a caller
- CI fails on assertions about inflight request counts, connection counts, or ref-counted resources

## Verified Workflow

### Quick Reference

```bash
# Find all callers of the function that adopted the context manager
grep -rn "_handle_webhook\|_inflight\b" src/ tests/

# Look for manual increment/decrement pairs that duplicate what the context manager does
grep -n "self\._inflight [+-]= 1" src/
```

### Detailed Steps

1. **Identify the new context manager** — find the `@contextmanager` (or `__enter__`/`__exit__`) that now owns the counter:
   ```python
   @contextmanager
   def _inflight_context(self):
       self._inflight += 1
       try:
           yield
       finally:
           self._inflight -= 1
   ```

2. **Identify the callee that adopted it** — confirm the internal method now uses it:
   ```python
   def _handle_webhook(self, ...):
       with self._inflight_context():
           # process
   ```

3. **Grep every caller of the callee** across the entire codebase:
   ```bash
   grep -rn "_handle_webhook" src/ tests/
   ```

4. **Audit each caller for stale manual lifecycle code**:
   ```python
   # STALE — caller still doing manual +1/-1 that the context manager now owns
   def receive_webhook(self, ...):
       self._inflight += 1        # ← REMOVE THIS
       self._handle_webhook(...)
       self._inflight -= 1        # ← REMOVE THIS
   ```

5. **Remove the stale lines** from every caller. The context manager is now the sole owner.

6. **Run the full test suite** to confirm the counter assertion returns to expected value:
   ```bash
   pytest tests/ -k "inflight" -v
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assume the context manager was enough | Introduced `_inflight_context()` in `_handle_webhook` and opened PR without checking callers | `receive_webhook()` still had manual `+1/-1`, causing double-increment; test observed `[2]` | Refactor PRs that move lifecycle into a context manager are INCOMPLETE until all callers are audited |
| Check only the test file for the bug | Searched tests for the assertion failure to find its root cause | The bug was in production code (`receive_webhook`), not in the test | Always search production code, not just tests, when counter values are unexpectedly doubled |

## Results & Parameters

**Symptom pattern:**
```
AssertionError: assert [2] == [1]
# or
AssertionError: inflight_counts == [1, 1] but got [2, 2]
```

**Root cause pattern:**
```python
# Context manager owns lifecycle (correct):
@contextmanager
def _inflight_context(self):
    self._inflight += 1
    try:
        yield
    finally:
        self._inflight -= 1

# Callee uses context manager (correct):
def _handle_webhook(self, ...):
    with self._inflight_context():
        ...

# STALE caller — double-increment bug:
def receive_webhook(self, ...):
    self._inflight += 1          # BUG: duplicates context manager
    self._handle_webhook(...)
    self._inflight -= 1          # BUG: duplicates context manager
```

**Fix:**
```python
def receive_webhook(self, ...):
    # No manual counter management — _handle_webhook owns it via _inflight_context
    self._handle_webhook(...)
```

**General principle:** When refactoring resource lifecycle into a context manager / RAII / try-finally pattern, GREP THE ENTIRE CODEBASE for prior manual lifecycle code in callers. The refactor PR is "incomplete" until those manual sites are also removed.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/ProjectHermes | PR #522, 2026-05-09 | `receive_webhook()` manually `+1`'d `_inflight` then called `_handle_webhook()` which uses `_inflight_context()` (+1 again). Test `test_inflight_increments_during_publish` expected `[1]` but got `[2]`. Fix: removed the redundant counter management from `receive_webhook`. |
