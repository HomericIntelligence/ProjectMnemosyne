---
name: logging-stdlib-json-formatter
description: "Build a zero-dependency JSON log formatter using stdlib logging.Formatter. Use when: (1) adding structured JSON logging to a shared library, (2) integrating Python logs with Loki/Promtail/ELK without adding dependencies."
category: tooling
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - logging
  - json
  - observability
  - stdlib
---

# Stdlib JSON Log Formatter (Zero Dependencies)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Add structured JSON logging to a shared Python library without introducing new dependencies |
| **Outcome** | Successful. `JsonFormatter` outputs single-line JSON records compatible with Loki/Promtail ingestion |
| **Verification** | verified-local |

## When to Use

- Adding structured/JSON logging to a Python project that wants to stay dependency-light
- Integrating Python logs with log aggregation systems (Loki, Promtail, ELK, Datadog)
- Extending a `ContextLogger` / `LoggerAdapter` pattern to emit structured output
- Need to handle extra/context fields as top-level JSON keys without collisions

## Verified Workflow

### Quick Reference

```python
import json
import logging
import traceback
from datetime import datetime, timezone

class JsonFormatter(logging.Formatter):
    RESERVED = frozenset({"timestamp", "level", "logger", "message", "exception", "stack_info"})
    _DEFAULT_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, None, None, None).__dict__.keys())

    def format(self, record: logging.LogRecord) -> str:
        log_dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),  # resolves lazy %s formatting
        }
        # Detect user-supplied extras by diffing against default LogRecord attrs
        extras = {k: v for k, v in record.__dict__.items() if k not in self._DEFAULT_ATTRS}
        for key, value in extras.items():
            if key in self.RESERVED:
                log_dict[f"ctx_{key}"] = value  # prefix collisions
            else:
                log_dict[key] = value
        if record.exc_info and record.exc_info[0] is not None:
            log_dict["exception"] = "".join(traceback.format_exception(*record.exc_info))
        if record.stack_info:
            log_dict["stack_info"] = record.stack_info
        return json.dumps(log_dict, default=str)  # default=str handles non-serializable
```

### Detailed Steps

1. **Subclass `logging.Formatter`** -- override `format()` to build a dict and serialize with `json.dumps()`
2. **Use `record.getMessage()`** for the message field -- this resolves lazy `%s` formatting that `record.msg` alone would miss
3. **Generate ISO 8601 timestamps with timezone** -- `datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()` produces `2026-03-25T10:00:00+00:00`
4. **Detect extra fields** by comparing `record.__dict__` against a snapshot of default `LogRecord` attributes. Build the snapshot once at module level: `frozenset(logging.LogRecord("", 0, "", 0, None, None, None).__dict__.keys())`
5. **Handle reserved field collisions** -- if a context key matches a reserved name (`timestamp`, `level`, `logger`, `message`, `exception`, `stack_info`), prefix it with `ctx_` to avoid silently overwriting the standard field
6. **Use `default=str`** in `json.dumps()` to safely serialize non-JSON-serializable objects (datetimes, custom classes, etc.)
7. **Wire into existing API** by adding a `json_format: bool = False` parameter to `get_logger()` and `setup_logging()`. When True, instantiate `JsonFormatter()` instead of `logging.Formatter(LOG_FORMAT)`

### Integration Pattern

```python
# Backward-compatible: json_format defaults to False
def get_logger(name: str, json_format: bool = False) -> ContextLogger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        formatter = JsonFormatter() if json_format else logging.Formatter(LOG_FORMAT)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return ContextLogger(logger)
```

### Context Fields Flow

When using a `LoggerAdapter` (like `ContextLogger`) that injects extra fields via `process()`:

```python
# ContextLogger.process() merges self._context into kwargs["extra"]
# logging framework sets these as attributes on the LogRecord
# JsonFormatter detects them by diffing against _DEFAULT_ATTRS
# They appear as top-level keys in the JSON output

logger = get_logger("svc", json_format=True)
bound = logger.bind(request_id="abc-123", service="keystone")
bound.info("Processing")
# {"timestamp":"...","level":"INFO","logger":"svc","message":"Processing","request_id":"abc-123","service":"keystone"}
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Use `python-json-logger` package | Considered adding as a dependency | Unnecessary complexity for a shared library that only depends on pyyaml; stdlib `json` + `logging.Formatter` does everything needed | Before adding a dependency, check if stdlib can do the job -- for JSON formatting it absolutely can |
| Access extra fields via `record.extra` attribute | LogRecord has no `.extra` attribute; extras are set as individual attributes on the record object | `logging.LoggerAdapter.process()` merges extras into `kwargs["extra"]`, but the framework then calls `setattr(record, key, value)` for each | Detect extras by diffing `record.__dict__` against a baseline snapshot of default LogRecord attributes |
| Use `record.msg` instead of `record.getMessage()` | `record.msg` is the raw format string (e.g. `"hello %s"`); args are not applied | `getMessage()` calls `self.msg % self.args` to produce the final string | Always use `record.getMessage()` in custom formatters to resolve lazy formatting |

## Results & Parameters

### Output Format

```json
{"timestamp": "2026-03-25T10:00:00.123456+00:00", "level": "INFO", "logger": "myapp.service", "message": "Request processed", "request_id": "abc-123", "duration_ms": 42}
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Zero new dependencies | Shared library consumed by many repos; minimize dependency surface |
| `default=str` in json.dumps | Gracefully handles non-serializable values instead of crashing |
| `ctx_` prefix for collisions | Silent data loss (overwriting `level` field) is worse than a renamed key |
| UTC timestamps | Log aggregation systems expect consistent timezone; UTC is the standard |
| Opt-in via `json_format=False` default | Full backward compatibility; existing callers unchanged |

### Test Patterns

```python
# Test JSON output validity
parsed = json.loads(formatter.format(record))
assert isinstance(parsed, dict)

# Test reserved field collision
record = make_record(extra={"level": "custom"})
parsed = json.loads(formatter.format(record))
assert parsed["level"] == "INFO"           # original preserved
assert parsed["ctx_level"] == "custom"     # collision prefixed

# Test non-serializable values
record = make_record(extra={"obj": CustomClass()})
parsed = json.loads(formatter.format(record))
assert parsed["obj"] == str(CustomClass())  # falls back to str()
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #45 - Structured JSON logging audit finding | PR #78, 451 tests pass, all lint clean |
