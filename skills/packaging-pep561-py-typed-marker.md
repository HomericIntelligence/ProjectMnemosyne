---
name: packaging-pep561-py-typed-marker
description: "Add PEP 561 py.typed marker to Python packages using hatchling. Use when: (1) making a typed Python package discoverable by mypy/pyright, (2) configuring hatch build targets for type marker files."
category: tooling
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags: [pep-561, py.typed, mypy, hatchling, packaging, typing]
---

# PEP 561 py.typed Marker for Hatchling Packages

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-25 |
| **Objective** | Add PEP 561 py.typed marker to a Python package using hatchling so type checkers recognize it as typed |
| **Outcome** | Successful — marker file created, build config updated, regression tests added |
| **Verification** | verified-precommit |

## When to Use

- A Python package has full type annotations but no `py.typed` marker file
- Type checkers (mypy, pyright) don't recognize the package as typed when imported as a dependency
- The project uses hatchling as its build backend and needs to ensure the marker ships in the wheel
- Adding PEP 561 compliance as a final step after enabling strict mypy settings

## Verified Workflow

> **Note:** Verified via pre-commit hooks (ruff, mypy, formatting). CI validation pending.

### Quick Reference

```bash
# 1. Create empty marker file
touch scylla/py.typed

# 2. Add to pyproject.toml hatch force-include
# Under [tool.hatch.build.targets.wheel.force-include]:
# "scylla/py.typed" = "scylla/py.typed"

# 3. Regenerate lock file if using pixi
pixi install

# 4. Run pre-commit to verify
pre-commit run --all-files
```

### Detailed Steps

1. **Create the empty marker file** at the package root (e.g., `scylla/py.typed`). The file must be empty per PEP 561.

2. **Add to hatch build targets** in `pyproject.toml`. Hatchling's `packages = ["scylla"]` directive includes Python files but may not include non-Python marker files. Add it explicitly to `[tool.hatch.build.targets.wheel.force-include]`:

   ```toml
   [tool.hatch.build.targets.wheel.force-include]
   "scylla/py.typed" = "scylla/py.typed"
   ```

3. **Regenerate the lock file** — adding the marker changes the package's SHA256 hash in the lock file. For pixi-managed projects, run `pixi install` to update `pixi.lock`.

4. **Write regression tests** to guard against accidental removal:
   - Test that `<package>/py.typed` exists as a file
   - Test that `pyproject.toml` includes it in `force-include`

5. **Verify** with `pre-commit run --all-files` — mypy should still pass with no regressions.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A — first implementation | Straightforward addition | N/A | The key insight is that hatchling `packages` directive only includes `.py` files; non-Python files like `py.typed` need `force-include` |

## Results & Parameters

**pyproject.toml addition:**

```toml
[tool.hatch.build.targets.wheel.force-include]
"scylla/py.typed" = "scylla/py.typed"
```

**Verification command:**

```bash
# After pip install, verify marker is in installed package
pip show -f scylla | grep py.typed
```

**Test file pattern** (`tests/unit/config/test_py_typed.py`):

```python
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

REPO_ROOT = Path(__file__).parents[3]

def test_py_typed_marker_exists() -> None:
    marker = REPO_ROOT / "scylla" / "py.typed"
    assert marker.is_file(), f"Missing PEP 561 marker: {marker}"

def test_py_typed_in_hatch_build_targets() -> None:
    with (REPO_ROOT / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    force_include = (
        data.get("tool", {}).get("hatch", {})
        .get("build", {}).get("targets", {})
        .get("wheel", {}).get("force-include", {})
    )
    assert "scylla/py.typed" in force_include
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Issue #1530 — PEP 561 compliance | PR #1559, pre-commit verified |
