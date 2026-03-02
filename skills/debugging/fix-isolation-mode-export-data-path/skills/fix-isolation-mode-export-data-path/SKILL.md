---
name: fix-isolation-mode-export-data-path
description: Fix ModuleNotFoundError when patching a scripts/ module that isn't on sys.path during single-file pytest runs; add sys.path guard to conftest.py
category: debugging
date: 2026-03-02
user-invocable: false
---

# Skill: Fix Isolation-Mode ModuleNotFoundError in conftest Patches

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-02 |
| **Objective** | Fix `ModuleNotFoundError: No module named 'export_data'` when `pytest tests/unit/analysis/test_figures.py` is run in isolation |
| **Outcome** | ✅ Success — single-file runs pass; `export_data` patches also applied, speeding up `test_export_data.py` |
| **Category** | Debugging |
| **Tags** | pytest, sys.path, isolation, conftest, mock, patch, scripts, pythonpath, ModuleNotFoundError |
| **Issue** | #1196 (follow-up from #1136) |
| **PR** | #1303 |

## When to Use This Skill

Use this skill when:

- `pytest <single-file>` fails with `ModuleNotFoundError: No module named '<script>'`
- The **full suite** passes but **single-file isolation** fails
- The module that's missing lives in `scripts/` (or another non-package directory added via `pyproject.toml` `pythonpath`)
- A `conftest.py` autouse fixture calls `unittest.mock.patch("scripts_module.something")` and the module isn't yet imported

**Trigger phrases:**
- "Tests pass in CI but fail when run directly with `pytest path/to/test.py`"
- "`ModuleNotFoundError` in conftest fixture setup, not in the test body"
- "Works when running the full suite but breaks on a subset"
- "patch target raises `ModuleNotFoundError` at fixture setup time"

## Root Cause

`pyproject.toml` sets `pythonpath = [".", "scripts"]`. When pytest is invoked on a
single file, rootdir detection still works, but **`pythonpath` injection only happens
reliably when pytest discovers its config via a full collection pass** from the project
root. In single-file mode, pytest may parse the ini file without fully processing
`pythonpath`.

The `mock_power_simulations` autouse fixture calls:
```python
patch("export_data.mann_whitney_power", ...)
```
`patch()` calls `importlib.import_module("export_data")` internally. If `scripts/` is
not yet on `sys.path`, this raises `ModuleNotFoundError` before any test body runs.

## Verified Workflow

### Step 1: Reproduce the failure

```bash
# Remove scripts from pythonpath override, run a test that doesn't import export_data
pixi run python -m pytest tests/unit/analysis/test_figures.py --override-ini="pythonpath=" -q
# ModuleNotFoundError: No module named 'export_data' (from conftest fixture setup)
```

### Step 2: Add sys.path guard to conftest.py

Add at the top of `tests/unit/analysis/conftest.py` (below standard imports, before any fixtures):

```python
import sys
from pathlib import Path

# Ensure scripts/ is importable when tests run in isolation.
# pyproject.toml sets pythonpath=[".", "scripts"] for full-suite runs,
# but rootdir detection may not inject it during single-file collection.
_scripts_dir = str(Path(__file__).parents[3] / "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)
```

**Key details:**
- `Path(__file__).parents[3]` navigates from `tests/unit/analysis/conftest.py` up 3 levels to the project root
- Adjust the `.parents[N]` index based on your conftest depth
- The guard `if _scripts_dir not in sys.path` prevents duplicate entries on full-suite runs

### Step 3: Extend the autouse fixture to patch the scripts module namespace

`export_data.py` does `from scylla.analysis.stats import mann_whitney_power`, binding
the name in `export_data`'s own namespace. You must patch that namespace too:

```python
@pytest.fixture(autouse=True)
def mock_power_simulations():
    with (
        patch("scylla.analysis.stats.mann_whitney_power", return_value=0.8),
        patch("scylla.analysis.stats.kruskal_wallis_power", return_value=0.75),
        patch("scylla.analysis.tables.comparison.mann_whitney_power", return_value=0.8),
        patch("scylla.analysis.tables.comparison.kruskal_wallis_power", return_value=0.75),
        patch("export_data.mann_whitney_power", return_value=0.8),       # NEW
        patch("export_data.kruskal_wallis_power", return_value=0.75),    # NEW
    ):
        yield
```

Note: Do **not** use `create=True` once the `sys.path` guard is in place — `export_data`
will be fully importable and `create=True` is unnecessary. If patching before the module
is loaded, `create=True` is needed instead of the sys.path guard.

### Step 4: Verify

```bash
# Single-file run — must now succeed
pixi run python -m pytest tests/unit/analysis/test_figures.py -q --no-cov

# Full suite — must still pass
pixi run python -m pytest tests/unit/analysis/ -q --no-cov

# Pre-commit (ruff will strip import if unused — that's fine, sys.path guard still runs)
pre-commit run --files tests/unit/analysis/conftest.py
```

**Important:** Ruff may remove a bare `import export_data` if added for side-effects
(F401 unused import). The `sys.path` guard block does not have this problem since it
uses no importable names — just modifies `sys.path`.

## Failed Attempts

### Attempt 1: Adding `import export_data` as a side-effect import

**What was tried:** Added `import export_data  # noqa: E402` after the sys.path guard to
force the module into `sys.modules` before any patching.

**Why it failed:** Ruff's F401 (unused import) hook removed the import since
`export_data` is never referenced by name in the conftest module scope. The pre-commit
hook auto-fixed the file, silently removing the guard.

**Fix:** The sys.path guard alone is sufficient — `patch("export_data....")` calls
`importlib.import_module("export_data")` internally, which works once `scripts/` is on
`sys.path`. No explicit import needed.

### Attempt 2: Assuming the test itself was broken

**What was tried:** Looking for errors in `test_figures.py` or its imports.

**Why it failed:** `test_figures.py` doesn't import `export_data` at all. The error
originates in `conftest.py`'s autouse fixture, which runs before any test body. This
is a conftest setup failure, not a test body failure.

**Lesson:** When `ModuleNotFoundError` appears before the first test runs, always check
`autouse` fixtures in conftest files up the directory tree.

## Results & Parameters

### Before vs After

| Scenario | Before | After |
|----------|--------|-------|
| `pytest tests/unit/analysis/test_figures.py` | `ModuleNotFoundError` (conftest setup) | 55 passed |
| `pytest tests/unit/analysis/test_export_data.py` | 27 passed, **23s** (unpatched power fns) | 27 passed, **23s** (patched — other stats still run) |
| `pytest tests/unit/analysis/` | 385 passed | 385 passed |
| Full suite | 3584 passed | 3584 passed |

Note: `test_export_data.py` runtime doesn't drop to <1s because `compute_statistical_results()`
calls many other statistics functions (Shapiro-Wilk, Spearman, etc.) that aren't mocked.
The power simulation mock prevents the worst-case 130s+ hang per test.

### The Complete conftest.py Patch (copy-paste)

```python
import sys
from pathlib import Path
from unittest.mock import patch
import pytest

# Ensure scripts/ is importable when tests run in isolation.
_scripts_dir = str(Path(__file__).parents[3] / "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)


@pytest.fixture(autouse=True)
def mock_power_simulations():
    """Mock expensive Monte Carlo simulations to prevent test hangs."""
    with (
        patch("scylla.analysis.stats.mann_whitney_power", return_value=0.8),
        patch("scylla.analysis.stats.kruskal_wallis_power", return_value=0.75),
        patch("scylla.analysis.tables.comparison.mann_whitney_power", return_value=0.8),
        patch("scylla.analysis.tables.comparison.kruskal_wallis_power", return_value=0.75),
        patch("export_data.mann_whitney_power", return_value=0.8),
        patch("export_data.kruskal_wallis_power", return_value=0.75),
    ):
        yield
```

### General Pattern for Any scripts/ Module

```python
# In conftest.py — add near top, before fixtures
import sys
from pathlib import Path

_scripts_dir = str(Path(__file__).parents[N] / "scripts")  # adjust N for conftest depth
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)
```

Where `N` = number of directory levels from conftest up to project root:
- `tests/conftest.py` → `parents[1]`
- `tests/unit/conftest.py` → `parents[2]`
- `tests/unit/analysis/conftest.py` → `parents[3]`
