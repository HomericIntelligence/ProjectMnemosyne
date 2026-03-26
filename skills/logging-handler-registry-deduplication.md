---
name: logging-handler-registry-deduplication
description: "Fix Python get_logger() adding duplicate handlers on repeated calls. Use when: (1) logger adds multiple StreamHandlers after repeated get_logger() calls, (2) file handler is silently skipped on second call, (3) parent logger propagation causes duplicate output."
category: debugging
date: 2026-03-25
version: "2.0.0"
user-invocable: false
verification: verified-local
history: logging-handler-registry-deduplication.history
tags:
  - python
  - logging
  - deduplication
  - handlers
---

# Logging Handler Registry Deduplication

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Fix `get_logger()` adding duplicate handlers when called multiple times for the same logger name, and allow incremental handler addition (e.g., file handler on second call) |
| **Outcome** | Successful — two verified approaches: module-level registry (v1) and isinstance-based inspection (v2) |
| **Verification** | verified-local (438 tests pass) |
| **History** | [changelog](./logging-handler-registry-deduplication.history) |

## When to Use

- `get_logger("name")` called multiple times produces duplicate log lines (one per call)
- `if not logger.handlers` guard prevents adding a file handler on a subsequent call
- Parent logger propagation causes double output (e.g., root logger + child logger both emit)
- Need to track which specific handlers have been configured per logger name
- Factory function wraps `logging.getLogger()` and needs idempotent handler setup

## Verified Workflow

Two approaches are verified. Choose based on complexity needs.

### Approach A: isinstance-based handler inspection (simpler, no external state)

Inspect `logger.handlers` directly with type checks. No module-level registry needed.

#### Quick Reference

```python
import os

def get_logger(name: str, log_file: str | None = None) -> logging.Logger:
    logger = logging.getLogger(name)

    # Console: only add if no StreamHandler (non-FileHandler) exists
    # IMPORTANT: FileHandler is a subclass of StreamHandler, so exclude it
    has_console = any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        for h in logger.handlers
    )
    if not has_console:
        logger.addHandler(logging.StreamHandler(sys.stdout))

    # File: only add if no FileHandler for this resolved path exists
    if log_file:
        resolved = os.path.abspath(log_file)
        has_file = any(
            isinstance(h, logging.FileHandler) and h.baseFilename == resolved
            for h in logger.handlers
        )
        if not has_file:
            logger.addHandler(logging.FileHandler(log_file))

    return logger
```

**Key gotcha**: `logging.FileHandler` is a subclass of `logging.StreamHandler`. The console handler check must use `and not isinstance(h, logging.FileHandler)` to avoid counting file handlers as console handlers.

### Approach B: Module-level registry (more explicit, handles custom handler types)

#### Quick Reference

```python
# Module-level registry — tracks handler keys per logger name
_configured_loggers: dict[str, set[str]] = {}

def get_logger(name: str, log_file: str | None = None) -> logging.Logger:
    logger = logging.getLogger(name)
    configured = _configured_loggers.setdefault(name, set())

    if "console" not in configured:
        logger.addHandler(logging.StreamHandler(sys.stdout))
        configured.add("console")

    if log_file and log_file not in configured:
        logger.addHandler(logging.FileHandler(log_file))
        configured.add(log_file)

    logger.propagate = False
    return logger
```

### Detailed Steps (both approaches)

1. **Replace `if not logger.handlers` with per-handler-type checks** — The naive guard fails because:
   - It's all-or-nothing: if handlers exist, no new ones can be added
   - It doesn't distinguish handler types (console vs file)
   - Python's logging hierarchy means `logger.handlers` can be empty while parent handles output

2. **Check each handler type independently**:
   - Console: only add if no console StreamHandler exists
   - File: only add if no FileHandler for the same resolved path exists

3. **Compare file paths using resolved absolute paths** — `FileHandler.baseFilename` stores the absolute path, so compare against `os.path.abspath(log_file)` to handle relative vs absolute equivalence

4. **Always update level** — Call `logger.setLevel()` on every invocation so subsequent calls with a different level take effect

5. **Consider `logger.propagate = False`** — Prevents parent loggers (especially root) from duplicating messages that child loggers already handle

### When to prefer each approach

| Criterion | Approach A (isinstance) | Approach B (registry) |
|-----------|------------------------|----------------------|
| External state | None | Module-level dict |
| Test cleanup | No cleanup needed | Must clear registry between tests |
| Custom handler types | Requires isinstance checks for each type | Just add a string key |
| Simplicity | Simpler for standard handlers | Better for complex handler setups |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `if not logger.handlers` guard | Check if logger already has any handlers before adding | All-or-nothing: blocks adding file handler on second call; doesn't prevent duplicates if handlers are removed and re-added | Track handler types individually, not just presence/absence |
| Check `type(h)` without attribute inspection | Inspect `type(h)` for existing handlers | Doesn't distinguish between two different file paths; would need to inspect `baseFilename` attribute | Must compare `baseFilename` (absolute path) to deduplicate file handlers |
| Rely on `propagate=True` (default) | Let parent loggers handle output | Parent + child both emit when both have handlers, causing duplicate lines | Set `propagate=False` on any logger that has its own handlers |
| isinstance check without FileHandler exclusion | Check `isinstance(h, logging.StreamHandler)` for console detection | FileHandler is a subclass of StreamHandler, so file handlers are counted as console handlers, preventing console handler from being added | Always use `isinstance(h, StreamHandler) and not isinstance(h, FileHandler)` for console detection |

## Results & Parameters

### Key behavior after fix

```python
# Repeated calls — no duplicate handlers
logger1 = get_logger("app")           # 1 StreamHandler
logger2 = get_logger("app")           # Still 1 StreamHandler

# Incremental handler addition works
logger3 = get_logger("app", log_file="app.log")  # 1 StreamHandler + 1 FileHandler

# Same file path doesn't duplicate
logger4 = get_logger("app", log_file="app.log")  # Still 1 StreamHandler + 1 FileHandler

# Level updates take effect
logger5 = get_logger("app", level=logging.DEBUG)  # Level changed to DEBUG
```

### Environment

- Python 3.10+
- Standard library `logging` module
- Works with `LoggerAdapter` wrappers (e.g., `ContextLogger`)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #32 — PR #70 | Fixed duplicate console handlers with registry approach, 389 tests pass |
| ProjectHephaestus | Issue #54 — PR #98 | Fixed file handler silently dropped on subsequent calls with isinstance approach, 438 tests pass |
