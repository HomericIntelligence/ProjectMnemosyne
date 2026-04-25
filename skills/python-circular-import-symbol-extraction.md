---
name: python-circular-import-symbol-extraction
description: "Fix Python circular import errors caused by partially-initialized modules by extracting the shared symbol into a new lightweight module. Use when: (1) Python raises ImportError or partially-initialized module error on startup, (2) module A imports module B which (lazily) imports module A, (3) the symbol being imported lives in A but A is only partially initialized when B tries to use it, (4) making imports lazy inside functions does not fix the error. After moving symbols, all mock patches must target the new module where the name is looked up at call time."
category: architecture
date: 2026-04-23
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - python
  - circular-imports
  - symbol-extraction
  - mock-patch
  - testing
---

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-23 |
| **Objective** | Break Python circular import chain `runner.py → tier_action_builder → subtest_executor.__getattr__ → parallel_executor → rate_limit → runner` that caused `ImportError` on startup |
| **Outcome** | Extracted `ShutdownInterruptedError`, `is_shutdown_requested`, `request_shutdown` into new `scylla/e2e/shutdown.py`; all importers redirected; `runner.py` re-exports symbols for backward compat; 4 test mock patches updated |
| **Verification** | verified-ci (ProjectScylla PR #1850) |

## When to Use

- Python raises `ImportError: cannot import name 'X' from partially initialized module 'A'` on startup
- `A → B → A` import cycle where A is only partially initialized when B tries to import from it
- Making imports lazy (moving `from X import Y` inside function bodies) does **not** fix the error — root cause is that Y is referenced during module init
- Multiple modules need a shared symbol and the symbol currently lives in a "heavy" module that creates the cycle
- After moving a symbol, test mock patches stop intercepting calls (patches targeting the old location no longer work)

## Verified Workflow

### Quick Reference

```text
Circular import diagnosis:
  1. Read the full ImportError traceback — map the import chain A → B → C → A
  2. Identify the shared symbol: which name is being imported across the cycle boundary?
  3. Ask: is this symbol lightweight (no heavy deps of its own)?
     YES → extract to new module C
     NO  → consider lazy import OR restructure dependencies

Fix pattern (symbol extraction):
  A imports C (not B)
  B imports C (not A)
  A re-exports from C for backward compat
  All mock patches updated to target C

Mock patch rule:
  Patch the module where the name is LOOKED UP at call time — not where it was originally defined.
  After moving symbol X from module A to module C:
    WRONG: patch("pkg.A.X", ...)    <- A no longer has X at call time
    RIGHT: patch("pkg.C.X", ...)    <- callers resolve X from C
```

### Step 1: Map the full circular import chain

Read the full traceback carefully. Python's partial-initialization error identifies the
module that is being imported while still being initialized:

```
ImportError: cannot import name 'is_shutdown_requested' from partially initialized
module 'scylla.e2e.runner' (most likely due to a circular import)
```

Trace the chain from the error:
```
runner.py
  -> tier_action_builder (imports runner for shutdown symbols)
  -> subtest_executor.__getattr__ triggers import of parallel_executor
  -> parallel_executor imports rate_limit
  -> rate_limit imports runner (cycle!)
```

### Step 2: Identify the lightweight shared symbols

List all symbols being imported across the cycle boundary. Ask for each:
- Does it have its own heavy dependencies that would re-create the cycle?
- Is it a pure value, function, or small exception class?

In the ProjectScylla case, the shared symbols were:
- `ShutdownInterruptedError` — simple Exception subclass, zero deps
- `is_shutdown_requested` — function reading a threading.Event, no heavy imports
- `request_shutdown` — function setting a threading.Event, no heavy imports

All three were safe to extract.

### Step 3: Create the new lightweight module

Create a new module at the same package level with only the extracted symbols and
their minimal dependencies:

```python
# src/scylla/e2e/shutdown.py
"""Shutdown coordination primitives (extracted to break circular imports).

This module intentionally has minimal dependencies so it can be imported by
any module in the scylla.e2e package without creating cycles.
"""
from __future__ import annotations

import threading

_shutdown_event = threading.Event()


class ShutdownInterruptedError(Exception):
    """Raised when a task is interrupted by a shutdown request."""


def is_shutdown_requested() -> bool:
    """Return True if a shutdown has been requested."""
    return _shutdown_event.is_set()


def request_shutdown() -> None:
    """Signal that a shutdown has been requested."""
    _shutdown_event.set()
```

**Key principle**: The new module must have NO imports that would re-create the cycle.
Verify this by checking every `import` in the new file against the existing chain.

### Step 4: Update all importers to use the new module

Redirect every module that was importing the symbols from the original location:

```python
# BEFORE (in rate_limit.py, parallel_executor.py, tier_action_builder.py, etc.):
from scylla.e2e.runner import ShutdownInterruptedError, is_shutdown_requested

# AFTER:
from scylla.e2e.shutdown import ShutdownInterruptedError, is_shutdown_requested
```

Search comprehensively — do not miss any importer:

```bash
grep -rn "from scylla.e2e.runner import" src/ tests/ --include="*.py"
grep -rn "from.*runner import.*shutdown\|from.*runner import.*Shutdown" src/ tests/ --include="*.py"
```

### Step 5: Add backward-compat re-exports to the original module

The original module (`runner.py`) should re-export the moved symbols so any code
that imports them from there still works:

```python
# In runner.py -- add at the top after other imports:
# Re-export shutdown primitives for backward compatibility.
# These were extracted to scylla.e2e.shutdown to break a circular import.
from scylla.e2e.shutdown import (  # noqa: F401  (re-export)
    ShutdownInterruptedError,
    is_shutdown_requested,
    request_shutdown,
)
```

The `# noqa: F401` suppresses the "imported but unused" linter warning since these
are intentional re-exports.

### Step 6: Update all mock patches in tests

**Critical**: After moving a symbol, any `unittest.mock.patch` or `pytest.monkeypatch`
that targets the **old** location will no longer intercept calls. The patch must target
the module where the name is **resolved at call time**.

Rule: patch the module that **imports and uses** the symbol, not where it was defined.

In the ProjectScylla case, `is_shutdown_requested` was moved from `runner` to `shutdown`.
The callers (e.g., `parallel_executor.py`) now import from `shutdown`. The patch target
changes accordingly:

```python
# BEFORE (broken after move -- patches a name that no longer exists in runner at call time):
@patch("scylla.e2e.runner.is_shutdown_requested", return_value=True)
def test_something(mock_shutdown):
    ...

# AFTER (correct -- patches the module where callers actually look up the name):
@patch("scylla.e2e.shutdown.is_shutdown_requested", return_value=True)
def test_something(mock_shutdown):
    ...
```

Find all affected patches:
```bash
grep -rn "patch.*runner.*is_shutdown_requested\|patch.*runner.*request_shutdown\|patch.*runner.*ShutdownInterrupted" tests/ --include="*.py"
```

Update each one. There may be 4-10 patches depending on test coverage.

### Step 7: Verify the fix

```bash
# Import the package from scratch (no cached modules)
python -c "from scylla.e2e import runner; print('OK')"

# Run the full test suite
pytest tests/ -v

# Check no imports still reference the old location for the moved symbols
grep -rn "from scylla.e2e.runner import.*shutdown\|from scylla.e2e.runner import.*Shutdown" src/ --include="*.py"
# Should return zero results (only the re-export line in runner.py itself)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Lazy imports inside function bodies | Moved `from scylla.e2e.runner import is_shutdown_requested` inside function bodies in rate_limit.py and parallel_executor.py | Did not fix the error -- the symbol was referenced during module-level code (class body, module-level constant) in one of the intermediate modules, so deferring the import statement didn't defer the actual resolution | Lazy function-body imports only help if the symbol is used at call time. If any intermediate module in the chain references the symbol during its own initialization (class definition, module constant), lazy imports don't break the cycle |
| Patching old module location after symbol move | 4 tests continued to use `patch("scylla.e2e.runner.is_shutdown_requested", ...)` after moving the symbol to `shutdown.py` | The patches registered the mock on `runner.is_shutdown_requested` but callers looked up `shutdown.is_shutdown_requested` -- the mock was never invoked, so tests passed without actually testing the behavior | Python mock patches intercept name lookups. After moving a symbol, update ALL patches to target the module where callers actually resolve the name |

## Results & Parameters

### New file created

```
src/scylla/e2e/shutdown.py   -- 3 symbols, ~40 lines, zero heavy deps
```

### Files updated

| File | Change |
|------|--------|
| `src/scylla/e2e/runner.py` | Added re-export block for backward compat |
| `src/scylla/e2e/rate_limit.py` | Updated import to `shutdown.py` |
| `src/scylla/e2e/parallel_executor.py` | Updated import to `shutdown.py` |
| `src/scylla/e2e/tier_action_builder.py` | Updated import to `shutdown.py` |
| `tests/unit/e2e/test_runner.py` | Updated 4 mock patches to target `shutdown` module |

### Dependency graph after fix

```
shutdown.py       (threading only -- zero scylla deps)
    ^
rate_limit.py     (imports from shutdown, not runner)
parallel_executor.py
tier_action_builder.py
    ^
runner.py         (imports from shutdown; re-exports for compat)
```

### Mock patch target rule (canonical)

```python
# Rule: patch where the name is LOOKED UP, not where it was DEFINED.

# Symbol defined in:   shutdown.py
# Symbol imported by:  parallel_executor.py  ->  from scylla.e2e.shutdown import is_shutdown_requested
# Correct patch target: "scylla.e2e.shutdown.is_shutdown_requested"

# If parallel_executor.py had done:
#   from scylla.e2e import shutdown
#   shutdown.is_shutdown_requested()
# Then the correct patch target would be:
#   "scylla.e2e.shutdown.is_shutdown_requested"  (same result here)

# If parallel_executor.py imports runner and accesses runner.is_shutdown_requested:
#   from scylla.e2e import runner
#   runner.is_shutdown_requested()
# Then the correct patch target would be:
#   "scylla.e2e.runner.is_shutdown_requested"  (the re-export in runner)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1850 -- circular import fix on `scylla.e2e` package | Fixed startup `ImportError`; 4 mock patches updated; CI passed |
