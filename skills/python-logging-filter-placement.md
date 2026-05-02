---
name: python-logging-filter-placement
description: 'Diagnose and fix Python logging KeyError from custom format fields.
  Use when: KeyError on %(custom_field)s, filter fields missing from output, or custom
  context not appearing in threaded logs.'
category: debugging
date: 2026-03-18
version: 1.0.0
user-invocable: false
---
# Python Logging Filter Placement

## Overview

| Attribute | Value |
| ----------- | ------- |
| **Problem** | `KeyError` or `ValueError` when using custom `%(field)s` placeholders in Python logging format strings |
| **Root Cause** | `logging.Filter` added to logger instead of handler; filter runs but fields may not reach formatter |
| **Fix** | Add filter to handler(s), not the logger |
| **Confidence** | High - verified with Python 3.10+ and 3.14t |

## When to Use

- `KeyError: 'custom_field'` or `ValueError: Formatting field not found in record: 'custom_field'` in logging output
- Custom `logging.Filter` that injects fields via `record.field = value` but fields are missing from formatted output
- Thread-local context (tier_id, request_id, etc.) not appearing in log lines
- Logging works in some threads but not others

## Verified Workflow

### Quick Reference

```python
# WRONG - filter on logger
logging.getLogger().addFilter(ContextFilter())

# RIGHT - filter on handler(s)
for handler in logging.getLogger().handlers:
    handler.addFilter(ContextFilter())
```

### Step 1: Understand the Python Logging Pipeline

```
Logger.handle()
  -> Logger.filter(record)     # Logger filters run here
  -> Logger.callHandlers()
     -> Handler.handle(record)
        -> Handler.filter(record)   # Handler filters run here
        -> Handler.emit(record)
           -> Formatter.format(record)  # %(field)s resolved here
```

Key insight: `Handler.handle()` calls `self.filter(record)` **before** `self.emit(record)` which calls `self.format(record)`. So handler filters are guaranteed to inject fields before formatting.

Logger filters also run before handlers, but in multi-threaded applications with propagation, the timing can be unreliable depending on Python version.

### Step 2: Fix the Filter Placement

Move `addFilter()` from the logger to its handler(s):

```python
# After logging.basicConfig() creates a StreamHandler:
for handler in logging.getLogger().handlers:
    handler.addFilter(ContextFilter())
```

### Step 3: Write Integration Tests

Test through `handler.handle()` (the real pipeline), not `handler.format()`:

```python
def test_handler_pipeline():
    handler = logging.StreamHandler()
    handler.addFilter(ContextFilter())
    handler.setFormatter(logging.Formatter(
        "[%(custom_field)s] %(message)s"
    ))

    record = logging.LogRecord(
        name="test", level=logging.INFO,
        pathname="", lineno=0,
        msg="test", args=(), exc_info=None,
    )

    # handle() runs filter -> emit -> format
    handler.handle(record)  # Must not raise
```

**Critical**: Do NOT test with `handler.format(record)` directly -- that skips the filter entirely and will always raise `KeyError`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Test with `handler.format()` | Called `handler.format(record)` to test the pipeline | `format()` does not invoke filters; only `handle()` runs `filter()` before `emit()`/`format()` | Always test through `handler.handle()` for integration tests |
| Filter on logger only | Added `ContextFilter` to root logger via `addFilter()` | In Python 3.14t with threaded workers, propagated loggers could miss the filter injection | Add filter to handlers for guaranteed field injection |

## Results & Parameters

### Environment

- Python 3.10+ (verified on 3.14.3 free-threaded build)
- Standard library `logging` module
- `ThreadPoolExecutor` worker threads

### Configuration Pattern

```python
import logging
from my_module import ContextFilter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(tier_id)s/%(subtest_id)s] %(message)s",
)

# Add filter to HANDLER, not logger
for handler in logging.getLogger().handlers:
    handler.addFilter(ContextFilter())
```

### ContextFilter Pattern

```python
import logging
import threading

_context = threading.local()

class ContextFilter(logging.Filter):
    def filter(self, record):
        record.tier_id = getattr(_context, "tier_id", "")
        record.subtest_id = getattr(_context, "subtest_id", "")
        return True

def set_log_context(*, tier_id="", subtest_id=""):
    _context.tier_id = tier_id
    _context.subtest_id = subtest_id
```
