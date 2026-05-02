# Session Notes: Python Logging Filter Placement Fix

## Date: 2026-03-18

## Context

PR #1515 in ProjectScylla introduced a `ContextFilter` and log format with `%(tier_id)s/%(subtest_id)s/%(run_num)s` placeholders. This crashed at runtime with `KeyError: 'tier_id'`.

## Root Cause

The `ContextFilter` was added to the root **logger** with `logging.getLogger().addFilter(ContextFilter())`, but `logging.basicConfig()` creates a `StreamHandler`. The format string with `%(tier_id)s` is evaluated by the handler's `Formatter.format()` method.

In Python's logging pipeline:
- `Logger.handle()` -> `Logger.filter()` -> `Logger.callHandlers()` -> `Handler.handle()` -> `Handler.filter()` -> `Handler.emit()` -> `Formatter.format()`

While logger filters technically run before handler processing, in threaded environments (Python 3.14t free-threaded build with `ThreadPoolExecutor`), the injection was unreliable.

## Fix Applied

**File**: `scripts/manage_experiment.py:74`

```python
# Before (broken):
logging.getLogger().addFilter(ContextFilter())

# After (fixed):
for _handler in logging.getLogger().handlers:
    _handler.addFilter(ContextFilter())
```

## Test Written

Added `TestHandlerFormatterIntegration` in `tests/unit/e2e/test_log_context.py` with 2 tests that exercise the full `handler.handle()` pipeline.

Key discovery during testing: `handler.format(record)` does NOT invoke filters. Only `handler.handle(record)` runs the `filter() -> emit() -> format()` pipeline. Initial test used `handler.format()` directly and failed with the same `KeyError`.

## Additional Observation

The `[//]` empty context in main-thread logs is expected behavior, not a bug. `set_log_context()` is only called inside worker threads in `parallel_executor.py:546` and `subtest_executor.py:527`. Main-thread logs (startup, tier setup, scheduler init) will always show empty context.

## PR

- ProjectScylla PR #1516: fix(logging): move ContextFilter from logger to handler
- Auto-merge enabled, 4926 tests passed, 77.74% coverage
