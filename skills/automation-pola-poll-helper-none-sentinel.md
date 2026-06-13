---
name: automation-pola-poll-helper-none-sentinel
description: "Use None as early-exit sentinel in poll helpers instead of returning a union of data+result. Use when: (1) a helper returns union[DataType, ResultType] where ResultType is the caller's responsibility, (2) instanceof discrimination pollutes call sites, (3) a poll/scan helper is constructing terminal WorkerResult objects."
category: architecture
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: []
---

# POLA: Poll Helper None-Sentinel Pattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Refactor poll helper that returns `tuple[Data] | WorkerResult` to return `tuple[Data] | None`, preserving caller ownership of result construction |
| **Outcome** | Successful — single-responsibility poll helper, cleaner caller, no isinstance discrimination |
| **Verification** | verified-ci |

## When to Use

- A helper returns a union of "data payload" and "terminal result object" — e.g., `tuple[list, list] | WorkerResult`
- The caller uses `isinstance(result, WorkerResult)` (or similar type dispatch) to decide next steps
- The terminal result object is straightforward and belongs conceptually to the caller's layer
- You're reviewing code for POLA (Principle of Least Astonishment) violations in poll/scan helpers

## Verified Workflow

### Quick Reference

```python
# BEFORE (overloaded — poll helper constructs caller's result):
def _poll_until_done(...) -> tuple[list, list] | WorkerResult:
    if not checks:
        return WorkerResult(success=True, pr_number=pr_number)  # wrong layer
    if deadline_exceeded:
        return WorkerResult(success=True, pr_number=pr_number)  # wrong layer
    return checks, required_checks

# Caller:
poll_result = self._poll_until_done(...)
if isinstance(poll_result, WorkerResult):      # isinstance discrimination
    return poll_result
checks, required_checks = poll_result

# AFTER (None sentinel — caller owns result construction):
def _poll_until_done(...) -> tuple[list, list] | None:
    if not checks:
        return None   # signal early-exit only
    if deadline_exceeded:
        return None   # signal early-exit only
    return checks, required_checks

# Caller:
poll_result = self._poll_until_done(...)
if poll_result is None:                        # simple identity check
    return WorkerResult(issue_number=issue_number, success=True, pr_number=pr_number)
checks, required_checks = poll_result
```

### Detailed Steps

1. Identify all early-return paths in the helper that return a `WorkerResult` (or equivalent terminal type)
2. Note what fields the `WorkerResult` contained — replicate these in the caller
3. Change all `return WorkerResult(...)` in the helper to `return None`
4. Update the return type annotation: `tuple[X, Y] | WorkerResult` → `tuple[X, Y] | None`
5. Update the docstring: "Returns `(checks, required_checks)` when concluded, or `None` when no checks exist or the poll deadline is exceeded"
6. In the caller, replace `isinstance(result, WorkerResult)` with `if result is None:`
7. In the caller, add the `WorkerResult` construction (using fields originally in the helper)
8. Update any tests: `assert isinstance(result, WorkerResult)` → `assert result is None`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Keep union as-is | Leave `tuple | WorkerResult` return type and document it | POLA violation flagged in PR review — surprising contract for a "poll" function | Poll helpers should be data-only; terminal state belongs to calling layer |
| Use Optional alias | `Optional[tuple[list, list]]` instead of explicit `| None` | No functional issue, just style — `| None` is more explicit in Python 3.10+ | Either works; `X | None` reads more clearly at a glance |

## Results & Parameters

**Concrete before/after for `ci_driver.py`** (commit `44c95ce6`, PR #1296):

```python
# Return type change:
# Before: tuple[list[dict[str, Any]], list[dict[str, Any]]] | WorkerResult
# After:  tuple[list[dict[str, Any]], list[dict[str, Any]]] | None

# Early-exit path 1 (no checks found):
# Before: return WorkerResult(issue_number=issue_number, success=True, pr_number=pr_number)
# After:  return None

# Early-exit path 2 (poll deadline exceeded):
# Before: return WorkerResult(issue_number=issue_number, success=True, pr_number=pr_number)
# After:  return None

# Caller check:
# Before: if isinstance(poll_result, WorkerResult):
#             return poll_result
# After:  if poll_result is None:
#             return WorkerResult(issue_number=issue_number, success=True, pr_number=pr_number)
```

**Test update pattern**:

```python
# Before:
assert isinstance(result, WorkerResult)
assert result.success is True
assert result.pr_number == 42

# After:
assert result is None
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #1296 (issue #1180 god-function decomposition) | `_poll_ci_until_concluded` in `hephaestus/automation/ci_driver.py` |
