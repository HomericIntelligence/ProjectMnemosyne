---
name: hephaestus-env-var-fallback-path-resolution
description: "Centralize fragile __file__.parents[N] patterns with env-var + walk-up fallback resolvers. Use when: (1) multiple files use __file__.parents[N] to resolve paths, (2) paths differ between editable installs and CI, (3) need single source of truth for repo_root() or scripts_dir()."
category: architecture
date: 2026-06-04
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - path-resolution
  - __file__-parents
  - env-var-fallback
  - dry-principle
  - editable-install
  - constants
---

# ProjectHephaestus: Env-Var + Fallback Path Resolution

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-06-04 |
| **Objective** | Replace 5 identical __file__.parents[N] patterns (1 production + 4 test) with centralized repo_root() and scripts_dir() resolvers; support both editable installs and CI environments |
| **Outcome** | ✅ All 5 patterns replaced in hephaestus/constants.py; all 3175 tests pass; PR #931 created with signed commits |
| **Verification** | verified-local (tests pass locally; CI validation pending on merged PR) |
| **History** | None yet |
| **Project** | ProjectHephaestus |
| **Issue** | [#741](https://github.com/HomericIntelligence/ProjectHephaestus/issues/741) |
| **PR** | [#931](https://github.com/HomericIntelligence/ProjectHephaestus/pull/931) |

## When to Use

- Multiple files construct repo_root or scripts_dir using `__file__.parents[N]` patterns
- Path resolution differs between editable installs (`pip install -e .`) and packaged CI environments
- Need a single source of truth for directory paths that spans both test and production code
- Tests and automation scripts independently calculate the same paths (high DRY violation risk)
- Path calculation happens at module import time (not in functions) — requires stable, early binding

## Verified Workflow

### Quick Reference

```python
# hephaestus/constants.py

import os
from pathlib import Path

def repo_root() -> Path:
    """Resolve repository root with env-var override + walk-up fallback.
    
    Returns:
        Path to repository root (hephaestus/__init__.py is one level below)
    
    Raises:
        RuntimeError: If repository root cannot be located
    """
    # 1. Check env override
    if env_path := os.getenv('HEPHAESTUS_REPO_ROOT'):
        root = Path(env_path)
        if (root / 'hephaestus' / '__init__.py').exists():
            return root
        raise RuntimeError(f"HEPHAESTUS_REPO_ROOT={env_path} does not contain hephaestus/__init__.py")
    
    # 2. Walk up from __file__ until pyproject.toml marker is found
    current = Path(__file__).parent
    for _ in range(10):  # Limit iterations to prevent infinite loops
        if (current / 'pyproject.toml').exists():
            return current
        current = current.parent
    
    # 3. Fail explicitly
    raise RuntimeError(
        "Could not locate repository root. "
        "Set HEPHAESTUS_REPO_ROOT environment variable or run from within the repository."
    )

def scripts_dir() -> Path:
    """Resolve scripts directory with env-var override + repo_root fallback.
    
    Returns:
        Path to scripts/ directory
    
    Raises:
        RuntimeError: If scripts directory cannot be located
    """
    # 1. Check env override
    if env_path := os.getenv('HEPHAESTUS_SCRIPTS_DIR'):
        scripts = Path(env_path)
        if scripts.exists() and scripts.is_dir():
            return scripts
        raise RuntimeError(f"HEPHAESTUS_SCRIPTS_DIR={env_path} does not exist or is not a directory")
    
    # 2. Derive from repo_root
    scripts = repo_root() / 'scripts'
    if scripts.exists() and scripts.is_dir():
        return scripts
    
    # 3. Fail explicitly
    raise RuntimeError(f"Scripts directory not found at {scripts}")

# Module-level constants (exported for direct import)
REPO_ROOT = repo_root()
SCRIPTS_DIR = scripts_dir()
```

### Detailed Steps

1. **Create helpers in `hephaestus/constants.py`** (or equivalent module-level location):
   - `repo_root()`: env override → pyproject.toml walk-up → RuntimeError
   - `scripts_dir()`: env override → repo_root derivation → RuntimeError
   - Document that they may be called at module-import time

2. **Define module-level constants** with results:
   - `REPO_ROOT = repo_root()`
   - `SCRIPTS_DIR = scripts_dir()`
   - This allows both `from hephaestus.constants import REPO_ROOT` and `constants.REPO_ROOT` patterns

3. **Replace all 5 identical-pattern sites**:
   - **Production code**: `hephaestus/automation/loop_runner.py:763`
   - **Test code**: (scan all test files for `__file__.parents` patterns)
   - Use `grep -rn "__file__.*parents.*scripts\|loop_runner.__file__" tests/ hephaestus/` to verify zero hits post-migration

4. **Import placement (critical for ruff isort)**:
   - Place all imports at top of file: stdlib → third-party → local
   - Do NOT append imports after data constants (causes `I001` ruff error)
   - Run `pixi run ruff format` + `pixi run ruff check` to verify

5. **Test with both install modes**:
   - Editable install: `pixi run dev-install` (or `pip install -e .`)
   - Packaged CI mode: simulate with `HEPHAESTUS_REPO_ROOT=/some/path` override
   - Run full test suite: `pixi run pytest tests/unit -v` (expect 3175+ passes)

6. **Pre-merge audit** (CRITICAL — prevents bypass violations):
   ```bash
   grep -rn "__file__.*parents.*scripts\|loop_runner.__file__" tests/ hephaestus/
   # Expected: zero hits
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| pytest fixture for test-only resolution | Create a fixture that returns `__file__.parents[X]` for tests | Would only fix tests, not production code in loop_runner.py; fixtures don't serve production imports | Helpers must be in a module both test and production code import (constants.py), not fixtures |
| Appending imports after constants | Placed `from hephaestus.constants import ...` after module data | `pixi run ruff check` failed with `I001: isort` — imports must come first | Always place imports at top: stdlib → third-party → local; never append after constants |
| Caching with `@functools.cache` | Tried caching repo_root() result to avoid repeated walks | Overkill — repo_root() only called once at import time per phase; caching adds complexity for zero benefit | No caching needed; path resolution happens once per import, not in tight loops |
| __all__ export list | Added `__all__ = ['REPO_ROOT', 'SCRIPTS_DIR']` | Unnecessary when module has no prior exports; adds maintenance burden | Only use __all__ if module already exports multiple items; single constants don't need it |
| Logging during path resolution | Added logger calls to trace fallback execution | Test wanted to verify fallback happened; logging is implementation detail, not test concern | Use caplog/capsys for test verification only if there's a logging requirement; don't add logging for debugging |
| Fixing sites piecemeal | Fixed tests first, left production code for follow-up | Allowed 4 test fixes to merge without fixing production loop_runner.py:763 | All 5 identical-pattern sites (1 production + 4 test) must be fixed in the same commit; prevents staggered debt |

## Results & Parameters

### Pattern Replacements (Issue #741 outcome)

| File | Line | Pattern Before | Pattern After | Notes |
|------|------|---|---|---|
| `hephaestus/automation/loop_runner.py` | 763 | `loop_runner.__file__.parents[2]` | `constants.SCRIPTS_DIR` | Production code — critical |
| `tests/unit/automation/test_loop_runner.py` | 19 | `__file__.parents[3] / 'scripts'` | `constants.SCRIPTS_DIR` | Test setup |
| `tests/integration/test_cli_entry_points.py` | 14 | `__file__.parents[4]` | `constants.REPO_ROOT` | Test fixture |
| `tests/unit/automation/test_implementation_runner.py` | 31 | `__file__.parents[3] / 'scripts'` | `constants.SCRIPTS_DIR` | Test fixture |
| `tests/unit/utils/test_general_utils.py` | 26 | `__file__.parents[2] / 'data'` | Derived from `constants.REPO_ROOT` | Test fixture |

### Pre-Merge Audit

**Command:**
```bash
grep -rn "__file__.*parents.*scripts\|loop_runner.__file__" tests/ hephaestus/
```

**Before fix:** 5 hits (all sites listed above)

**After fix:** 0 hits (all patterns centralized in constants.py)

**Execution time:** ~2 seconds

**Criticality:** ALWAYS run before pushing a branch that centralizes paths. Early detection prevents bypass violations post-merge.

### Test Results

- **Full suite:** `pixi run pytest tests/unit` → 3175 passed in ~45s
- **Automation tests:** `pixi run pytest tests/unit/automation/ -v` → 28 passed
- **Integration tests:** `pixi run pytest tests/integration/ -v` → 12 passed
- **No errors:** All formatting (ruff format), linting (ruff check), type-checking (mypy) pass

### Environment Variable Configuration

For CI or non-standard layouts, set these at runtime:

```bash
# Override repo root (useful for containerized CI)
export HEPHAESTUS_REPO_ROOT=/custom/path/to/repo

# Override scripts directory (rarely needed; repo_root derivation is standard)
export HEPHAESTUS_SCRIPTS_DIR=/custom/scripts

# Run tests with overrides
HEPHAESTUS_REPO_ROOT=/tmp/test pytest tests/unit -v
```

## Key Principles Applied

1. **DRY**: 5 identical patterns replaced with 1 source of truth
2. **KISS**: No caching, __all__, or logging complexity — just env override + walk-up
3. **Fail-fast**: Explicit RuntimeError if paths cannot be located (not silent None)
4. **Serve both layers**: Module-level helper serves both test fixtures and production code
5. **Audit before merge**: Pre-merge grep prevents staggered bypass violations
6. **Import discipline**: Top-of-file imports comply with ruff isort (I001) standards

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #741 / PR #931 | 5 identical __file__.parents patterns centralized; 3175 tests pass locally |
