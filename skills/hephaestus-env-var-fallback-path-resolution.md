---
name: hephaestus-env-var-fallback-path-resolution
description: "Centralize fragile __file__.parents[N] patterns with env-var + walk-up fallback resolvers, and avoid the worktree+editable-install trap where a __file__-anchored repo-root walk-up silently resolves to a PARENT meta-repo / sibling checkout that shares the marker file (making a checker read the WRONG file). Use when: (1) multiple files use __file__.parents[N] to resolve paths, (2) paths differ between editable installs and CI, (3) need single source of truth for repo_root() or scripts_dir(), (4) a get_repo_root()/marker-file walk-up runs inside a git worktree nested under a meta-repo or monorepo with nested pyproject.toml, (5) a validator/checker PASSES even on injected-violation input and you suspect repo-root/path resolution, (6) choosing between `python -m pkg.mod` and `python path/to/shim.py` to invoke an installed entry point."
category: architecture
date: 2026-06-12
version: "1.1.0"
user-invocable: false
verification: verified-ci
history: hephaestus-env-var-fallback-path-resolution.history
tags:
  - path-resolution
  - __file__-parents
  - env-var-fallback
  - dry-principle
  - editable-install
  - constants
  - git-worktree
  - pip-install-e
  - get_repo_root
  - repo-root-resolution
  - python-m-vs-script
  - pep660
  - marker-file-walkup
  - verification-fidelity
---

# ProjectHephaestus: Env-Var + Fallback Path Resolution

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-06-12 (v1.1.0); 2026-06-04 (v1.0.0) |
| **Objective** | (v1.0.0) Replace 5 identical __file__.parents[N] patterns with centralized repo_root()/scripts_dir(). (v1.1.0) Capture the worktree+editable-install failure mode where a __file__-anchored marker walk-up resolves to the PARENT meta-repo and a checker reads the WRONG pyproject.toml, plus the `python -m pkg.mod` fix and the verification-fidelity lesson |
| **Outcome** | ✅ (v1.0.0) 5 patterns centralized, 3175 tests pass, PR #931. (v1.1.0) Root-caused a "checker passes on injected violation" bug to repo-root resolution reading the parent meta-repo; switched the CI step to `python -m hephaestus.scripts_lib.check_version_single_source`; `deps/version-sync` passed in CI (13s) |
| **Verification** | verified-ci (deps/version-sync gate passed in CI after the `-m` fix; PR #1266) |
| **History** | `hephaestus-env-var-fallback-path-resolution.history` (v1.0.0 archived) |
| **Project** | ProjectHephaestus |
| **Issue** | [#741](https://github.com/HomericIntelligence/ProjectHephaestus/issues/741), [#1181](https://github.com/HomericIntelligence/ProjectHephaestus/issues/1181) |
| **PR** | [#931](https://github.com/HomericIntelligence/ProjectHephaestus/pull/931), [#1266](https://github.com/HomericIntelligence/ProjectHephaestus/pull/1266) |

## When to Use

- Multiple files construct repo_root or scripts_dir using `__file__.parents[N]` patterns
- Path resolution differs between editable installs (`pip install -e .`) and packaged CI environments
- Need a single source of truth for directory paths that spans both test and production code
- Tests and automation scripts independently calculate the same paths (high DRY violation risk)
- Path calculation happens at module import time (not in functions) — requires stable, early binding
- **(v1.1.0) A `__file__`-anchored marker walk-up (`get_repo_root()`) runs inside a git worktree nested under a meta-repo, or in a monorepo with nested `pyproject.toml` / `.git` markers** — the first ancestor with the marker may NOT be the intended root
- **(v1.1.0) A validator/checker PASSES even on injected-violation input** — suspect repo-root/path resolution reading a sibling/parent file BEFORE suspecting the checker logic
- **(v1.1.0) Choosing how to invoke an installed entry point** — prefer `python -m pkg.mod` over `python path/to/shim.py`; the script-path form lets `sys.path[0]`/CWD/editable-finder interaction land `__file__` outside the worktree

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

### Worktree + Editable-Install Trap (v1.1.0)

**The failure mode.** `get_repo_root(start_path)` walks UP from `start_path`,
returning the first dir containing a `.git` entry OR a `pyproject.toml` marker.
When the code is checked out in a **git worktree** nested under a meta-repo
(e.g. `<meta-repo>/build/.worktrees/issue-1181/`) and installed editable
(`pip install -e .`, PEP 660), and the **parent meta-repo itself contains a
`pyproject.toml`**, the marker is AMBIGUOUS — more than one ancestor matches.

Observed on ProjectHephaestus #1181 / #1266: a version-single-source checker
reported PASS even with an injected `[project].version` violation, because it
resolved repo root to the PARENT meta-repo's clean `pyproject.toml` instead of
the worktree's. The checker logic was correct; it read the WRONG file.

- Run as a **module** → `python -m hephaestus.scripts_lib.check_version_single_source`
  → module `__file__` stays the literal worktree path; walk-up stops at the
  worktree root → correctly detected the violation (exit 1).
- Run as a **script shim** → `python scripts/check_version_single_source.py`
  → `sys.path[0]` / editable-finder interaction materialized `__file__`
  (and a CWD-seeded `get_repo_root()` fallback) OUTSIDE the worktree, on the
  parent checkout that shares the marker → read the clean parent pyproject
  (exit 0). Violation masked.

**The fix (verified-ci).** Invoke installed-package entry points as MODULES:
`python -m package.module`, NOT `python path/to/shim.py`. The `-m` form makes
module `__file__` and import resolution unambiguous and immune to
`sys.path[0]`/CWD-dependent resolution, so a `__file__`-anchored
`get_repo_root()` anchors to the installed package and reads the checked-out
tree you intend. In a plain CI checkout (no nested worktree, no sibling marker)
the script-path form also works — but `-m` is strictly more robust and is the
canonical way to run an installed module. The repo's CI step was switched to
`-m`; `deps/version-sync` passed in CI (13s).

**Verification fidelity (the headline lesson).** LOCAL verification of
`__file__`-anchored tooling run from inside a git worktree is **untrustworthy**.
A marker-file walk-up is AMBIGUOUS whenever more than one ancestor has the
marker — exactly a worktree nested under a meta-repo that is itself a Python
project, or any monorepo with nested `pyproject.toml`. It returns the FIRST
match walking up, which may not be the intended root. When a validator passes
on known-bad input, verify WHICH file it read before touching its logic, and
confirm with a synthetic FAIL.

**Diagnostic probe.** Print the resolved root and the file actually read, and
compare against the worktree path you expect:

```python
from hephaestus.scripts_lib.check_version_single_source import get_repo_root, _load_toml
rr = get_repo_root()  # or pass an explicit, correct start_path seed
print("resolved repo_root:", rr)
print("version read:", _load_toml(rr / "pyproject.toml").get("project", {}).get("version"))
# If rr points at a PARENT/SIBLING checkout instead of your worktree, that's the bug.
```

Also: a CWD-seeded `get_repo_root()` (default `Path.cwd()` when no `start_path`)
and `__pycache__` compound the confusion. Always pass an explicit, correct seed
and confirm it equals the worktree root.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| pytest fixture for test-only resolution | Create a fixture that returns `__file__.parents[X]` for tests | Would only fix tests, not production code in loop_runner.py; fixtures don't serve production imports | Helpers must be in a module both test and production code import (constants.py), not fixtures |
| Appending imports after constants | Placed `from hephaestus.constants import ...` after module data | `pixi run ruff check` failed with `I001: isort` — imports must come first | Always place imports at top: stdlib → third-party → local; never append after constants |
| Caching with `@functools.cache` | Tried caching repo_root() result to avoid repeated walks | Overkill — repo_root() only called once at import time per phase; caching adds complexity for zero benefit | No caching needed; path resolution happens once per import, not in tight loops |
| __all__ export list | Added `__all__ = ['REPO_ROOT', 'SCRIPTS_DIR']` | Unnecessary when module has no prior exports; adds maintenance burden | Only use __all__ if module already exports multiple items; single constants don't need it |
| Logging during path resolution | Added logger calls to trace fallback execution | Test wanted to verify fallback happened; logging is implementation detail, not test concern | Use caplog/capsys for test verification only if there's a logging requirement; don't add logging for debugging |
| Fixing sites piecemeal | Fixed tests first, left production code for follow-up | Allowed 4 test fixes to merge without fixing production loop_runner.py:763 | All 5 identical-pattern sites (1 production + 4 test) must be fixed in the same commit; prevents staggered debt |
| Assumed the checker was buggy (v1.1.0) | Edited/instrumented the version-single-source checker logic because it PASSED with an injected static `[project].version` | Logic was correct; root cause was repo-root resolution reading the PARENT meta-repo's clean pyproject.toml inside a worktree | When a validator passes on known-bad input, verify WHICH file it read before touching its logic |
| Suspected stale bytecode (v1.1.0) | Used `python -B` and purged `__pycache__` | Behavior unchanged; not a bytecode issue | Rule out path/repo-root resolution before bytecode |
| Ran the shim "how CI calls it" (v1.1.0) | `python scripts/check_version_single_source.py` to mirror CI | Inside the worktree this resolved repo_root to the parent meta-repo (sibling pyproject marker), masking the violation | Prefer `python -m pkg.mod`; it removes the `sys.path[0]`/`__file__` ambiguity |
| Trusted a local clean PASS (v1.1.0) | Treated a local PASS as proof the gate works | The PASS came from reading the WRONG file (parent checkout) | Confirm resolved repo_root equals the worktree before trusting any result; verify with a synthetic FAIL |
| Relied on `get_repo_root()` default seed (v1.1.0) | Let a probe use the default `Path.cwd()` seed | Returned the meta-repo root, not the worktree | Always seed the resolver explicitly; CWD and `__file__` can both leak outside a worktree |

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

### Repo-Root Walk-Up Contract & the `-m` Fix (v1.1.0)

| Parameter | Value |
|-----------|-------|
| **`get_repo_root(start_path)` contract** | Walks UP from `start_path`, returns the FIRST ancestor containing a `.git` entry OR a `pyproject.toml` marker; module seeds it with `Path(__file__).resolve().parent`; default `start_path` is `Path.cwd()` when omitted |
| **Ambiguity condition** | More than one ancestor has the marker — a worktree nested under a meta-repo that is itself a Python project, or a monorepo with nested `pyproject.toml` |
| **Symptom** | Checker/validator returns PASS (exit 0) on injected-violation input because it read a parent/sibling file |
| **Robust invocation (fix)** | `python -m package.module` — unambiguous module `__file__`, immune to `sys.path[0]`/CWD |
| **Fragile invocation** | `python path/to/shim.py` — `sys.path[0]`/editable-finder can land `__file__` outside the worktree |
| **CI result** | After switching the gate step to `-m`, `deps/version-sync` passed in CI (~13s) |

**Diagnostic snippet (compare resolved root vs your worktree):**
```python
from hephaestus.scripts_lib.check_version_single_source import get_repo_root, _load_toml
rr = get_repo_root()
print(rr, _load_toml(rr / "pyproject.toml").get("project", {}).get("version"))
```

### Cross-Links

- `hephaestus-env-var-fallback-path-resolution` (this skill) — env-var override + walk-up resolver design
- `architecture-python-src-layout-migration` — src-layout & editable-install packaging context
- `git-worktree-sys-path-precedence-issue` — companion: worktree `sys.path` ordering loads STALE CODE in subprocess console scripts (different failure: wrong code vs. this skill's wrong data file)
- Companion CI dead-required-gate learning (ProjectHephaestus #1181/#1266) — the worktree repo-root resolution bug is WHY the dead-gate verification initially looked like it passed

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
| ProjectHephaestus | Issue #1181 / PR #1266 | Worktree+editable-install repo-root resolution masked an injected version violation; switching the gate step to `python -m hephaestus.scripts_lib.check_version_single_source` fixed it; `deps/version-sync` passed in CI (~13s) — verified-ci |
