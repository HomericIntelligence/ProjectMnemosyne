---
name: python-circular-import-symbol-extraction
description: "Fix Python circular import errors caused by partially-initialized modules. Use when: (1) Python raises ImportError or partially-initialized module error on startup, (2) module A imports module B which imports back into A while A is still loading, (3) __init__.py eagerly re-exports heavyweight CLI modules that import back into the same package, (4) making imports lazy inside functions does not fix the error. Fix: remove eager re-exports from __init__.py, extract the shared symbol to a true leaf module, redirect all importers to the leaf. After moving symbols, all mock patches must target the new module where the name is looked up at call time."
category: architecture
date: 2026-04-29
version: "1.1.0"
user-invocable: false
verification: verified-local
history: python-circular-import-symbol-extraction.history
tags:
  - python
  - circular-imports
  - symbol-extraction
  - mock-patch
  - testing
  - eager-init-exports
---

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-29 |
| **Objective** | Break Python circular import chains that produce `ImportError: cannot import name 'X' from partially initialized module` on startup |
| **Outcome** | Two verified fixes: (1) ProjectScylla PR #1850 — extract shutdown symbols to leaf module; (2) ProjectHephaestus PR #308 — remove eager CLI re-exports from `__init__.py` + extract `_gh_call` to leaf module |
| **Verification** | verified-local (PR #308: pre-commit passed, unit tests passed; CI pending) / verified-ci (PR #1850) |
| **History** | [changelog](./python-circular-import-symbol-extraction.history) |

## When to Use

- Python raises `ImportError: cannot import name 'X' from partially initialized module 'A'` on startup
- `A → B → A` import cycle where A is only partially initialized when B tries to import from it
- `package/__init__.py` eagerly re-exports CLI entry-point modules (via `from pkg.cli_mod import main`) and those CLI modules import back into the same package
- Making imports lazy (moving `from X import Y` inside function bodies) does **not** fix the error — root cause is that Y is referenced during module init
- Multiple modules need a shared symbol and the symbol currently lives in a "heavy" module that creates the cycle
- After moving a symbol, test mock patches stop intercepting calls (patches targeting the old location no longer work)

## Verified Workflow

### Quick Reference

```text
Step 0: Check __init__.py for eager CLI re-exports (new trigger in v1.1.0)
  - Look for lines like: from pkg.fleet_sync import main as fleet_sync
  - CLI entry-point modules often import back into the package = instant cycle
  - Fix: delete those lines and remove names from __all__

Circular import diagnosis:
  1. Read the full ImportError traceback — map the import chain A → B → C → A
  2. Identify the shared symbol: which name is being imported across the cycle boundary?
  3. Ask: is this symbol lightweight (no heavy deps of its own)?
     YES → extract to new leaf module
     NO  → consider lazy import OR restructure dependencies

Fix pattern (symbol extraction):
  __init__.py   removes eager re-export of CLI modules
  cli_mod.py    imports from leaf (not from the package being initialized)
  leaf.py       has NO imports that touch the package being initialized
  orig.py       re-exports from leaf for backward compat (explicit `as X` form for mypy)

Mock patch rule:
  Patch the module where the name is LOOKED UP at call time — not where it was originally defined.
  After moving symbol X from module A to leaf module C:
    WRONG: patch("pkg.A.X", ...)    <- A no longer has X at call time
    RIGHT: patch("pkg.C.X", ...)    <- callers resolve X from C
```

### Step 0: Check `__init__.py` for eager CLI re-exports

Before tracing the full chain, check whether the cycle is *triggered by* `__init__.py` loading
a heavyweight CLI module:

```python
# hephaestus/github/__init__.py  <-- PROBLEMATIC pattern
from hephaestus.github.fleet_sync import main as fleet_sync  # CLI module!
from hephaestus.github.tidy import main as tidy              # CLI module!
__all__ = [..., "fleet_sync", "tidy"]
```

CLI modules typically import everything they need, including utilities that live in the same
package. When `hephaestus.github` is first loaded (e.g., by `from hephaestus.automation.github_api import _gh_call`),
it triggers loading of `fleet_sync`, which tries `from hephaestus.automation.github_api import _gh_call`
— but `hephaestus.github` is not yet done initializing at that moment.

**Fix**: delete the eager re-export lines and remove the names from `__all__`. Callers that need the CLI
modules can import them directly (`from hephaestus.github.fleet_sync import main`).

```python
# hephaestus/github/__init__.py  <-- FIXED
# (removed fleet_sync and tidy re-exports)
__all__ = [...]  # CLI entry points removed
```

### Step 1: Map the full circular import chain

Read the full traceback carefully. Python's partial-initialization error identifies the
module that is being imported while still being initialized:

```
ImportError: cannot import name '_gh_call' from partially initialized
module 'hephaestus.github' (most likely due to a circular import)
```

Trace the chain from the error:
```
# ProjectHephaestus PR #308 example:
hephaestus.github.__init__
  -> fleet_sync (eagerly imported by __init__)
  -> from hephaestus.automation.github_api import _gh_call
  -> github_api imports from hephaestus.github (cycle!)

# ProjectScylla PR #1850 example:
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

In the ProjectHephaestus case, the shared symbol was:
- `_gh_call` — subprocess helper function; only deps are `rate_limit.py` + `run_subprocess`

In the ProjectScylla case, the shared symbols were:
- `ShutdownInterruptedError` — simple Exception subclass, zero deps
- `is_shutdown_requested` — function reading a threading.Event, no heavy imports
- `request_shutdown` — function setting a threading.Event, no heavy imports

All were safe to extract.

### Step 3: Create the new lightweight leaf module

Create a new module at the same package level with only the extracted symbols and
their minimal dependencies. The leaf module must import ONLY stdlib + lower-level helpers —
never from the package being initialized:

```python
# hephaestus/github/gh_subprocess.py — leaf module
"""gh subprocess helper extracted to break circular imports.

This module intentionally has minimal dependencies so it can be imported by
any module in the hephaestus.github package without creating cycles.
"""
from hephaestus.github.rate_limit import detect_claude_usage_limit, detect_rate_limit, wait_until
from hephaestus.utils.helpers import run_subprocess


def _gh_call(args, check=True, retry_on_rate_limit=True, max_retries=3):
    ...
```

```python
# src/scylla/e2e/shutdown.py — leaf module
"""Shutdown coordination primitives (extracted to break circular imports)."""
import threading

_shutdown_event = threading.Event()

class ShutdownInterruptedError(Exception): ...
def is_shutdown_requested() -> bool: ...
def request_shutdown() -> None: ...
```

**Key principle**: The new module must have NO imports that would re-create the cycle.
Verify this by checking every `import` in the new file against the existing chain.

### Step 4: Update all importers to use the new leaf module

Redirect every module that was importing the symbols from the original location:

```python
# fleet_sync.py: BEFORE
from hephaestus.automation.github_api import _gh_call

# fleet_sync.py: AFTER
from hephaestus.github.gh_subprocess import _gh_call
```

```python
# BEFORE (in rate_limit.py, parallel_executor.py, etc.):
from scylla.e2e.runner import ShutdownInterruptedError, is_shutdown_requested

# AFTER:
from scylla.e2e.shutdown import ShutdownInterruptedError, is_shutdown_requested
```

Search comprehensively — do not miss any importer:

```bash
grep -rn "from <pkg>.<original_module> import <symbol>" src/ tests/ --include="*.py"
```

### Step 5: Add backward-compat re-exports to the original module

The original module should re-export the moved symbols so any code that imports them
from there still works. Use the explicit `as X` form — required by mypy for re-exports:

```python
# automation/github_api.py — explicit re-export (mypy requires `as X` form)
from hephaestus.github.gh_subprocess import _gh_call as _gh_call
```

```python
# In runner.py — backward compat re-export block:
from scylla.e2e.shutdown import (  # noqa: F401  (re-export)
    ShutdownInterruptedError,
    is_shutdown_requested,
    request_shutdown,
)
```

The `# noqa: F401` suppresses the "imported but unused" linter warning. The explicit
`as _gh_call` form (rather than just `import _gh_call`) signals to mypy that this is
an intentional public re-export — without it mypy raises `error: Module does not explicitly export attribute`.

### Step 6: Update all mock patches in tests

**Critical**: After moving a symbol, any `unittest.mock.patch` or `pytest.monkeypatch`
that targets the **old** location will no longer intercept calls. The patch must target
the module where the name is **resolved at call time**.

Rule: patch the module that **imports and uses** the symbol, not where it was defined.

```python
# BEFORE (broken after move):
@patch("scylla.e2e.runner.is_shutdown_requested", return_value=True)

# AFTER (correct):
@patch("scylla.e2e.shutdown.is_shutdown_requested", return_value=True)
```

Find all affected patches:
```bash
grep -rn "patch.*<original_module>.*<symbol_name>" tests/ --include="*.py"
```

### Step 7: Verify the fix

```bash
# Import the package from scratch (no cached modules)
python -c "from hephaestus.automation.planner import main; print('OK')"
python -c "from scylla.e2e import runner; print('OK')"

# Run the full test suite
pytest tests/ -v

# Check no imports still reference the old location for the moved symbols
grep -rn "from <pkg>.<original_module> import <symbol>" src/ --include="*.py"
# Should return zero results (only the re-export line itself)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Lazy imports inside function bodies | Moved `from scylla.e2e.runner import is_shutdown_requested` inside function bodies in rate_limit.py and parallel_executor.py | Did not fix the error — the symbol was referenced during module-level code (class body, module-level constant) in one of the intermediate modules, so deferring the import statement didn't defer the actual resolution | Lazy function-body imports only help if the symbol is used at call time. If any intermediate module in the chain references the symbol during its own initialization, lazy imports don't break the cycle |
| Patching old module location after symbol move | 4 tests continued to use `patch("scylla.e2e.runner.is_shutdown_requested", ...)` after moving the symbol to `shutdown.py` | The patches registered the mock on `runner.is_shutdown_requested` but callers looked up `shutdown.is_shutdown_requested` — the mock was never invoked | Python mock patches intercept name lookups. After moving a symbol, update ALL patches to target the module where callers actually resolve the name |
| Delete only `__init__.py` re-exports without moving `_gh_call` | Removed `fleet_sync`/`tidy` from `hephaestus/github/__init__.py` but left `from hephaestus.automation.github_api import _gh_call` in `fleet_sync.py` | The `github → automation` import edge in `fleet_sync.py` remained intact; any future code path touching both packages can re-trigger the same cycle | Must eliminate the layering violation at the source (move the shared symbol to a leaf module), not just remove the eager load from `__init__.py` |
| Lazy import inside the offending function in fleet_sync.py | Moved `from hephaestus.automation.github_api import _gh_call` inside the function body | Mechanically avoids the startup cycle but leaves a hidden trap — no CI check enforces it; future refactors can promote it back to module level | Use a structural fix (move the symbol to a leaf module) rather than a runtime workaround; structural fixes are enforced by the import graph itself |

## Results & Parameters

### New leaf modules created

```
hephaestus/github/gh_subprocess.py  -- _gh_call only, imports rate_limit + run_subprocess
src/scylla/e2e/shutdown.py          -- 3 symbols, ~40 lines, zero heavy deps
```

### Files updated (ProjectHephaestus PR #308)

| File | Change |
|------|--------|
| `hephaestus/github/__init__.py` | Removed eager re-exports of `fleet_sync` and `tidy`; removed from `__all__` |
| `hephaestus/github/gh_subprocess.py` | New leaf module containing `_gh_call` |
| `hephaestus/github/fleet_sync.py` | Updated import to `gh_subprocess` (from `automation.github_api`) |
| `hephaestus/automation/github_api.py` | Added explicit re-export: `from hephaestus.github.gh_subprocess import _gh_call as _gh_call` |

### Files updated (ProjectScylla PR #1850)

| File | Change |
|------|--------|
| `src/scylla/e2e/runner.py` | Added re-export block for backward compat |
| `src/scylla/e2e/rate_limit.py` | Updated import to `shutdown.py` |
| `src/scylla/e2e/parallel_executor.py` | Updated import to `shutdown.py` |
| `src/scylla/e2e/tier_action_builder.py` | Updated import to `shutdown.py` |
| `tests/unit/e2e/test_runner.py` | Updated 4 mock patches to target `shutdown` module |

### Dependency graph after fix (ProjectHephaestus)

```
gh_subprocess.py   (rate_limit + run_subprocess only — no automation deps)
    ^
fleet_sync.py      (imports from gh_subprocess, not automation.github_api)
    ^
github/__init__.py (no longer eagerly loads fleet_sync or tidy)
    ^
automation/github_api.py  (re-exports _gh_call from gh_subprocess for compat)
```

### Mock patch target rule (canonical)

```python
# Rule: patch where the name is LOOKED UP, not where it was DEFINED.

# Symbol defined in:   shutdown.py
# Symbol imported by:  parallel_executor.py  ->  from scylla.e2e.shutdown import is_shutdown_requested
# Correct patch target: "scylla.e2e.shutdown.is_shutdown_requested"
```

### Explicit re-export form required by mypy

```python
# WRONG (mypy error: Module does not explicitly export attribute '_gh_call'):
from hephaestus.github.gh_subprocess import _gh_call

# RIGHT (mypy accepts explicit re-export):
from hephaestus.github.gh_subprocess import _gh_call as _gh_call
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1850 — circular import fix on `scylla.e2e` package | Fixed startup `ImportError`; 4 mock patches updated; CI passed |
| ProjectHephaestus | PR #308 — eager `__init__.py` re-exports triggering circular import | Removed CLI re-exports from `github/__init__.py`; extracted `_gh_call` to `gh_subprocess.py`; pre-commit passed, unit tests passed locally |
