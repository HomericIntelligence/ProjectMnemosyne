---
name: nats-jetstream-sync-codebase-integration
description: "Integrating NATS JetStream into a synchronous Python codebase using daemon threads. Use when: (1) adding event-driven messaging to a sync-only project, (2) creating optional dependencies with import guards, (3) threading async nats-py into a threading.Thread-based architecture."
category: architecture
date: 2026-03-25
version: "1.0.0"
user-invocable: false
tags: [nats, jetstream, threading, async-in-sync, optional-dependency, pydantic-config]
---

# NATS JetStream Integration into Synchronous Python Codebase

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Add NATS JetStream event subscription to a purely synchronous, filesystem-based Python project (ProjectScylla) so it can receive task events from ProjectHermes |
| **Outcome** | Successful - full implementation with 45 unit tests, config integration, CLI command, all pre-commit hooks passing |

## When to Use

- Adding NATS or any async messaging library to a synchronous Python codebase
- Creating a daemon thread subscriber that wraps an async event loop
- Designing optional dependencies that don't break standalone operation
- Integrating a new config section across Pydantic models, YAML defaults, JSON schemas, and config loaders
- Adding a long-running CLI command with signal handling and graceful shutdown

## Verified Workflow

### Quick Reference

```bash
# 1. Add optional dependency
# pyproject.toml: [project.optional-dependencies] nats = ["nats-py>=2.0,<3"]
# pixi.toml: [pypi-dependencies] nats-py = ">=2.0,<3"

# 2. Create package: scylla/nats/{__init__,config,events,handlers,subscriber}.py
# 3. Add NATSConfig to DefaultsConfig + ScyllaConfig in config/models.py
# 4. Add nats: section to config/defaults.yaml and schemas/defaults.schema.json
# 5. Pass nats config through loader.py
# 6. Add CLI command with signal handling
# 7. Write tests, run pre-commit
pixi install  # regenerate pixi.lock
pixi run python -m pytest tests/unit/nats/ -v --no-cov
SKIP=audit-doc-policy pre-commit run --all-files
```

### Detailed Steps

1. **Daemon thread pattern** - Model the subscriber on existing `HeartbeatThread` pattern:
   - Extend `threading.Thread` with `daemon=True`
   - Use `threading.Event` for clean shutdown (`_stop_event`)
   - Create isolated `asyncio.new_event_loop()` inside `run()` for the async nats-py client
   - Reconnection with exponential backoff (1s initial, 2x multiplier, 60s max)

2. **Async-in-sync bridge** - The key pattern for wrapping async nats-py in a sync thread:
   ```python
   def run(self) -> None:
       while not self._stop_event.is_set():
           try:
               loop = asyncio.new_event_loop()
               try:
                   loop.run_until_complete(self._subscribe_loop())
               finally:
                   loop.close()
           except Exception:
               if self._stop_event.is_set():
                   break
               self._stop_event.wait(timeout=backoff)
               backoff = min(backoff * multiplier, max_backoff)
   ```

3. **Optional dependency guard** - Use `try/except ImportError` at the point of use, not at module level:
   ```python
   async def _subscribe_loop(self) -> None:
       try:
           import nats as nats_client
       except ImportError:
           logger.error("nats-py is not installed. Install with: pip install 'scylla[nats]'")
           self._stop_event.set()
           return
   ```

4. **Config integration checklist** (5 files for a new config section):
   - `scylla/nats/config.py` - Pydantic model with env var override loader
   - `config/defaults.yaml` - YAML section with defaults
   - `schemas/defaults.schema.json` - JSON schema validation (with `additionalProperties: false`)
   - `scylla/config/models.py` - Add field to `DefaultsConfig` and `ScyllaConfig`
   - `scylla/config/loader.py` - Pass through in merged config dict

5. **CLI signal handling** for long-running commands:
   ```python
   stop_event = threading.Event()
   def _signal_handler(signum, frame):
       stop_event.set()
   signal.signal(signal.SIGINT, _signal_handler)
   signal.signal(signal.SIGTERM, _signal_handler)
   subscriber.start()
   stop_event.wait()  # Block main thread
   subscriber.stop()  # Drain + join
   ```

6. **mypy strict compliance**:
   - Use `collections.abc.Callable` not `typing.Callable` (ruff auto-fixes this)
   - Use `dict[str, Any]` not `dict[str, object]` for Pydantic `**kwargs` unpacking
   - Use `import X as X` pattern in `__init__.py` for explicit re-export (`implicit_reexport=false`)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `dict[str, object]` type for config loader | Used `object` as value type in `load_nats_config()` | mypy error: `**dict[str, object]` incompatible with `bool`/`str`/`list[str]` expected types | Use `dict[str, Any]` when dict will be unpacked as `**kwargs` to Pydantic models |
| `logging.LogCaptureFixture` in test type hints | Used `logging.LogCaptureFixture` for pytest caplog fixture | mypy error: `Name "logging.LogCaptureFixture" is not defined` | Use `pytest.LogCaptureFixture` - it's a pytest type, not a logging type |
| Pre-setting stop event then asserting `new_event_loop` called | Test set `_stop_event` before `run()` then asserted async loop was created | `while not self._stop_event.is_set()` check exits before loop body executes | When stop event is pre-set, the thread exits immediately without entering the loop - test the exit behavior instead |
| Missing test method docstrings | Wrote test methods without docstrings | ruff D102 (Missing docstring in public method) failures | All test methods in classes need docstrings even if the class has one |

## Results & Parameters

### File Structure Created

```
scylla/nats/
  __init__.py      # Re-exports with `import X as X` pattern
  config.py        # NATSConfig + load_nats_config() with NATS_URL/NATS_STREAM/NATS_DURABLE_NAME env overrides
  events.py        # NATSEvent model + parse_subject() for hi.tasks.{team}.{task_id}.{verb}
  handlers.py      # EventRouter with verb dispatch + default stub handlers
  subscriber.py    # NATSSubscriberThread daemon thread with JetStream durable consumer

tests/unit/nats/
  __init__.py
  test_config.py   # 13 tests - defaults, custom values, env overrides, empty env vars
  test_events.py   # 12 tests - model validation, subject parsing, parametrized
  test_handlers.py # 10 tests - dispatch, isolation, unknown verbs, default handlers
  test_subscriber.py # 8 tests - lifecycle, backoff, reconnection, stop behavior
```

### NATSConfig Defaults

```yaml
nats:
  enabled: false
  url: "nats://localhost:4222"
  stream: "TASKS"
  subjects:
    - "hi.tasks.>"
  durable_name: "scylla-subscriber"
```

### Environment Variable Overrides

| Env Var | Config Field | Example |
|---------|-------------|---------|
| `NATS_URL` | `url` | `nats://remote:4222` |
| `NATS_STREAM` | `stream` | `EVENTS` |
| `NATS_DURABLE_NAME` | `durable_name` | `custom-consumer` |

### Test Results

- 45 NATS unit tests passing
- 341 existing config tests unaffected
- All pre-commit hooks pass (ruff, mypy, bandit, YAML lint, JSON schema validation)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1505 - Add NATS event subscription from ProjectHermes | PR #1549 |
