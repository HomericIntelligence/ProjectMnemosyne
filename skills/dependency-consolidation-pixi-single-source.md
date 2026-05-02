---
name: dependency-consolidation-pixi-single-source
description: "Consolidate Python dependency declarations across pixi.toml, pyproject.toml, and requirements*.txt into pixi.toml as the single source of truth. Use when: (1) dependencies are declared in multiple files with divergent version constraints, (2) pinned versions in requirements.txt conflict with pixi.toml ranges, (3) pyproject.toml duplicates dependency declarations already managed by pixi."
category: ci-cd
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - pixi
  - dependencies
  - pyproject
  - requirements
  - consolidation
  - ci-guardrail
---

# Dependency Consolidation: pixi.toml as Single Source of Truth

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-25 |
| **Objective** | Eliminate dependency declaration drift across pixi.toml, pyproject.toml, and requirements*.txt |
| **Outcome** | Successful — single source of truth in pixi.toml with auto-generated lockfiles and CI guardrail |
| **Verification** | verified-local (37 unit tests pass, pre-commit passes, CI pending on PR #5117) |

## When to Use

- Python dependencies are declared in multiple files (pixi.toml, pyproject.toml, requirements.txt) with divergent version constraints
- Pinned versions in requirements*.txt fall outside pixi.toml range constraints (e.g., `pytest==8.4.2` vs `<8`)
- pyproject.toml `[project.dependencies]` or `[project.optional-dependencies]` duplicates packages already managed by pixi
- Packages exist in requirements*.txt but not in pixi.toml (or vice versa)
- A security audit references non-existent files (e.g., `tools/requirements.txt`)

## Verified Workflow

### Quick Reference

```bash
# 1. Add all missing packages to pixi.toml [dependencies]
# 2. Remove [project.dependencies] and [project.optional-dependencies] from pyproject.toml
# 3. Regenerate requirements*.txt from pixi-resolved versions
pixi install
pixi run python scripts/sync_requirements.py

# 4. Verify consistency
pixi run python scripts/check_dep_sync.py
pixi run python scripts/sync_requirements.py --check

# 5. Run tests
pixi run python -m pytest tests/scripts/test_check_dep_sync.py tests/scripts/test_sync_requirements.py -v
```

### Detailed Steps

1. **Audit all dependency files** — Map every package across pixi.toml, pyproject.toml `[project.dependencies]`, pyproject.toml `[project.optional-dependencies]`, requirements.txt, and requirements-dev.txt. Identify:
   - Missing packages (in one file but not pixi.toml)
   - Version conflicts (pinned version outside pixi range)
   - Ghost references (CI/Dockerfiles referencing non-existent files)

2. **Add missing packages to pixi.toml** — Group by purpose with inline comments:
   ```toml
   [dependencies]
   # Testing
   pytest = ">=8.1.0,<9"
   pytest-xdist = ">=3.0.0,<4"

   # Code quality
   ruff = ">=0.14.7,<0.16"
   safety = ">=3.0.0,<4"

   # Documentation
   mkdocs = ">=1.6.0,<2"
   ```

3. **Strip pyproject.toml** — Remove `[project.dependencies]` and `[project.optional-dependencies]`. Keep `[tool.*]` sections (pytest, ruff, mypy, coverage config). Add header comment:
   ```toml
   # Dependencies are managed in pixi.toml (single source of truth).
   # This file provides project metadata and tool configuration only.
   ```

4. **Create sync script** (`scripts/sync_requirements.py`) — Reads `pixi list --json`, generates requirements.txt and requirements-dev.txt with exact pins and auto-generated header.

5. **Create CI guardrail** (`scripts/check_dep_sync.py`) — Validates:
   - Every package in requirements*.txt exists in pixi.toml
   - Pinned versions satisfy pixi.toml range constraints
   - pyproject.toml has no `[project.dependencies]` or `[project.optional-dependencies]`

6. **Add CI job** — Add `validate-dep-sync` job to comprehensive-tests.yml that runs `check_dep_sync.py` on every PR.

7. **Fix consuming files** — Update Dockerfiles (add lockfile comments), security.yml (remove ghost `tools/requirements.txt`), justfile (verify safety-check references).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Import via sys.path.insert | Used `sys.path.insert(0, PROJECT_ROOT)` then `from scripts.check_dep_sync import ...` | `scripts/` has no `__init__.py`, and pytest's import mechanism conflicts with sys.path hacks in Python 3.14 | Use `importlib.util.spec_from_file_location()` to load modules from scripts without `__init__.py` |
| Direct `from scripts.X import Y` | Standard Python package import | `scripts/` is not a Python package (no `__init__.py`), and adding one would be a broader change | When `scripts/` lacks `__init__.py`, use `importlib.util` for test imports |

## Results & Parameters

### Auto-generated requirements.txt format

```text
# AUTO-GENERATED from pixi.toml — do not edit manually.
# Regenerate with: python scripts/sync_requirements.py
# These files exist for pip-only contexts (Docker, CI fallback).

pytest==8.4.2
pytest-cov==6.3.0
ruff==0.14.14
jinja2==3.1.6  # Template engine (paper scaffolding, code generation)
```

### importlib.util pattern for test imports (scripts without __init__.py)

```python
import importlib.util
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_spec = importlib.util.spec_from_file_location(
    "check_dep_sync", _PROJECT_ROOT / "scripts" / "check_dep_sync.py"
)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

check_dep_sync = _mod.check_dep_sync
```

### Version constraint checking (pixi.toml range vs pinned version)

```python
def version_satisfies(version: Tuple[int, ...], constraints: List[VersionRange]) -> bool:
    for c in constraints:
        v = version + (0,) * max(0, len(c.version) - len(version))
        cv = c.version + (0,) * max(0, len(version) - len(c.version))
        if c.op == ">=" and not (v >= cv): return False
        if c.op == "<" and not (v < cv): return False
        # ... etc
    return True
```

### Key metrics

- 37 unit tests covering all validation and generation logic
- 8 packages added to pixi.toml (pytest-xdist, safety, mkdocs, mkdocs-material, pytest-benchmark, jinja2, pyyaml, click)
- 3 ghost references fixed in security.yml (`tools/requirements.txt` → `requirements-dev.txt`)
- 0 version conflicts remaining after consolidation

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #4907, PR #5117 | Consolidated deps across pixi.toml, pyproject.toml, requirements.txt, requirements-dev.txt |
