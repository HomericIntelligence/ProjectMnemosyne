---
name: architecture-metaclass-threadlocal-thread-safety
description: "Pattern for making class-level attribute access thread-safe using a metaclass with __getattr__ and threading.local(). Use when: (1) a class uses mutable class attributes shared across threads, (2) you need per-thread enable/disable state, (3) you want to preserve the Class.ATTR access pattern while eliminating shared mutable state."
category: architecture
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [thread-safety, metaclass, threading-local, python, immutable-state]
---

# Metaclass + threading.local() for Thread-Safe Class Attributes

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-25 |
| **Objective** | Replace mutable class-level state with per-thread computed access while preserving the `Class.ATTR` API |
| **Outcome** | Success — backward-compatible, thread-safe, 15 tests pass including concurrent access |
| **Verification** | verified-local |

## When to Use

- A class stores configuration as **mutable class attributes** (e.g., ANSI color codes, feature flags)
- Methods like `disable()` **mutate class attributes**, affecting all threads and modules simultaneously
- You need **per-thread state isolation** (one thread disabling doesn't affect others)
- You want to preserve the **`Class.ATTR` access pattern** (no API change for consumers)
- Python 3.10+ (no `__class_getattr__` available until 3.12)

## Verified Workflow

### Quick Reference

```python
import threading

_state = threading.local()

_CODES: dict[str, str] = {"OKGREEN": "\033[92m", "FAIL": "\033[91m"}

class _Meta(type):
    def __getattr__(cls, name: str) -> str:
        if name in _CODES:
            return _CODES[name] if getattr(_state, "enabled", True) else ""
        raise AttributeError(f"type object {cls.__name__!r} has no attribute {name!r}")

class Colors(metaclass=_Meta):
    @staticmethod
    def disable() -> None:
        _state.enabled = False

    @staticmethod
    def enable() -> None:
        _state.enabled = True
```

### Detailed Steps

1. **Extract values to an immutable dict**: Move all mutable class attributes into a module-level `dict[str, str]` that is never mutated.

2. **Add `threading.local()` state**: Create a module-level `_state = threading.local()` to hold per-thread boolean flags.

3. **Create a metaclass with `__getattr__`**: The metaclass intercepts attribute access on the class itself (not instances). Since the color names are no longer class attributes, Python falls through to `__getattr__` on every access.

4. **Compute on access**: In `__getattr__`, check the thread-local flag and return either the real value or an empty string.

5. **Replace mutating methods**: `disable()` and `enable()` now just set `_state.enabled = False/True` instead of overwriting 9+ class attributes.

6. **Default to enabled**: Use `getattr(_state, "enabled", True)` so new threads that haven't called `disable()` get colors by default.

### Why Metaclass (Not Other Approaches)

| Approach | Problem |
| ---------- | --------- |
| `threading.Lock` around mutations | Still global state — all threads share one enable/disable flag |
| Instance-based `Colors()` | Breaks the `Colors.ATTR` class-level access pattern used everywhere |
| `__class_getattr__` (PEP 657) | Python 3.12+ only, not available in 3.10 |
| Module-level `__getattr__` | Changes API from `Colors.ATTR` to `colors.ATTR` (module access) |
| **Metaclass `__getattr__`** | Works on 3.10+, preserves `Colors.ATTR`, per-thread via `threading.local()` |

### Testing Thread Safety

```python
import threading

def test_disable_does_not_affect_other_thread():
    barrier = threading.Barrier(2)
    results = {}

    def disabler():
        Colors.disable()
        barrier.wait(timeout=5)
        results["disabler"] = Colors.OKGREEN

    def reader():
        barrier.wait(timeout=5)
        results["reader"] = Colors.OKGREEN

    t1 = threading.Thread(target=disabler)
    t2 = threading.Thread(target=reader)
    t1.start(); t2.start()
    t1.join(timeout=5); t2.join(timeout=5)

    assert results["disabler"] == ""
    assert results["reader"] == "\033[92m"
```

Use `threading.Barrier` to synchronize threads so the reader checks *after* the disabler has called `disable()`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `typing.Dict` import | Used `from typing import Dict` for type annotation | Ruff UP035/UP006 flags it as deprecated in 3.10+ | Use builtin `dict[str, str]` directly |
| Import ordering | Put `from hephaestus... import Colors, _CODES, _state` | Ruff I001 wants underscore-prefixed names sorted first | Ruff sorts `_CODES` before `Colors` (leading underscore sorts before uppercase) |

## Results & Parameters

**Files changed**: 2
- `hephaestus/cli/colors.py`: Replaced 9 mutable class attributes + `disable()` mutation with metaclass + `threading.local()` pattern
- `tests/unit/cli/test_colors.py`: Rewrote 5 existing tests, added 5 thread-safety tests (15 total)

**Test results**: 15/15 pass, 100% coverage on `colors.py`, full suite 394/394 pass

**PR**: HomericIntelligence/ProjectHephaestus#68

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Issue #30 — thread-safe Colors class | PR #68, all 394 tests pass |
