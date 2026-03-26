---
name: tooling-structured-json-logging-stdlib
description: "Add structured JSON logging to a Python library using only stdlib. Use when: (1) adding json_format parameter to setup_logging(), (2) creating a JsonFormatter subclass of logging.Formatter, (3) filtering extra context fields from LogRecord for JSON output."
category: tooling
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [python, logging, json, structured-logging, stdlib, formatter]
---

# Add Structured JSON Logging with stdlib Only

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Add optional JSON-formatted log output to an existing Python logging setup without adding dependencies |
| **Outcome** | Successful — `setup_logging(json_format=True)` outputs valid JSON, backward-compatible, 387 tests pass |
| **Verification** | verified-local |

## When to Use

- A Python library has a `setup_logging()` function and needs machine-readable output for log aggregators
- You want structured logging without adding `structlog`, `python-json-logger`, or other dependencies
- An audit flags missing structured logging support (#45-style finding)
- You need to preserve existing `ContextLogger` extra fields in JSON output

## Verified Workflow

### Quick Reference

```python
# 1. Create JsonFormatter in logging/utils.py
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_ATTRS:
                log_entry.setdefault(key, value)
        return json.dumps(log_entry, default=str)

# 2. Add json_format parameter to setup_logging()
def setup_logging(..., json_format: bool = False) -> None:
    formatter = JsonFormatter() if json_format else logging.Formatter(format_string)
    # Apply formatter to all handlers

# 3. Export from __init__.py and lazy imports
```

### Detailed Steps

1. **Pre-compute standard LogRecord attributes** at module level to avoid creating a dummy record per `format()` call:

   ```python
   _STANDARD_RECORD_ATTRS = frozenset(
       logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
       | {"message", "msg", "args"}
   )
   ```

   This is computed once at import time. The frozen set is used to filter out standard attributes when building the JSON output, leaving only extra context fields from `ContextLogger.bind()`.

2. **Create `JsonFormatter`** as a subclass of `logging.Formatter`:
   - Use `record.getMessage()` (not `record.msg`) to get the formatted message with args applied
   - Include exception info only when present and non-None
   - Use `json.dumps(log_entry, default=str)` to handle non-serializable values safely
   - Use `setdefault` when adding extra fields to avoid overwriting core fields

3. **Add `json_format` parameter** to `setup_logging()`:
   - Default `False` for backward compatibility
   - When `True`, `format_string` parameter is ignored (note this in docstring)
   - Apply the formatter to ALL handlers (stdout, stderr, file) — don't create handlers first then set formatter

4. **Export the new class**:
   - Add to subpackage `__init__.py` (`__all__` and imports)
   - Add to top-level `_LAZY_IMPORTS` dict for `hephaestus.JsonFormatter` access

5. **Write tests** — three test cases cover the feature:
   - `test_output_is_valid_json`: Create a LogRecord manually, format it, `json.loads()` the output, assert fields
   - `test_includes_exception`: Use `try/except/sys.exc_info()` to create a record with exception info
   - `test_json_format`: Call `setup_logging(json_format=True)`, verify handlers have `JsonFormatter` instances

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Creating dummy LogRecord inside `format()` | `logging.LogRecord("", 0, "", 0, "", (), None)` called per format invocation to filter standard attrs | Wasteful — creates a new object for every log line | Pre-compute the standard attribute set at module level as a `frozenset` |
| Using `record.__dict__` directly without filtering | Iterated `record.__dict__` and included all keys in JSON | JSON output contained internal attributes like `relativeCreated`, `thread`, `processName`, etc. | Filter using a pre-computed set of standard `LogRecord` attribute names |
| Setting `format` kwarg on `basicConfig` with `json_format=True` | Passed `format=format_string` to `logging.basicConfig()` even when `json_format=True` | The `format` kwarg overrides handler formatters in some cases | When using custom formatters, set them on handlers explicitly and omit `format` from `basicConfig()` |

## Results & Parameters

### JsonFormatter Output Format

```json
{
  "timestamp": "2026-03-25 14:30:00,123",
  "name": "hephaestus.io.utils",
  "level": "INFO",
  "message": "Processing 42 files",
  "request_id": "abc-123"
}
```

The `request_id` field comes from `ContextLogger.bind(request_id="abc-123")` — any extra context fields are automatically included.

### Exception Output

```json
{
  "timestamp": "2026-03-25 14:30:00,456",
  "name": "hephaestus.io.utils",
  "level": "ERROR",
  "message": "Failed to write file",
  "exception": "Traceback (most recent call last):\n  File ..."
}
```

### Integration with Existing ContextLogger

No changes needed to `ContextLogger` — it adds context via `kwargs["extra"]` which becomes attributes on the `LogRecord`. The `JsonFormatter` picks these up automatically by iterating `record.__dict__` and filtering out standard attributes.

### Key Design Decision: Module-Level Attribute Set

```python
# Computed once at import time — O(1) lookup per attribute during formatting
_STANDARD_RECORD_ATTRS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
    | {"message", "msg", "args"}
)
```

The `| {"message", "msg", "args"}` is needed because:
- `message` is added by `Formatter.format()`, not in `__init__`
- `msg` and `args` are the raw template and arguments (we use `getMessage()` instead)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #45, PR #88 | Added `JsonFormatter` + `json_format` param, 387 unit tests pass, 82.20% coverage |
