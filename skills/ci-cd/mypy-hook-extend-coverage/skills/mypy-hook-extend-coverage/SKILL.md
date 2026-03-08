---
name: mypy-hook-extend-coverage
description: "Extend mypy pre-commit hook coverage to additional directories with baseline suppression. Use when: ruff covers more dirs than mypy, tests/tools have annotation drift, or hyphenated directory names cause module resolution conflicts."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Goal** | Extend mypy pre-commit hook from `scripts/` to `tests/` and `tools/` directories |
| **Languages** | Python, YAML, INI |
| **Config Files** | `.pre-commit-config.yaml`, `mypy.ini`, `pyproject.toml` |
| **Hook Type** | `mirrors-mypy` (isolated virtualenv) |
| **Key Risk** | Hyphenated directory names + `ignore_errors` scoping |

## When to Use

- mypy hook `files:` pattern is narrower than ruff's (e.g., only `scripts/` but ruff covers `tests/` too)
- New directories have Python files with type annotation drift that should be caught incrementally
- Pre-existing type errors in expanded dirs would immediately break the hook if naively added
- You need to understand why `[[tool.mypy.overrides]]` in `pyproject.toml` isn't suppressing errors

## Verified Workflow

### Step 1: Triage each directory for mypy errors

```bash
pixi run mypy --ignore-missing-imports --explicit-package-bases --python-version 3.10 tests/ 2>&1 | tail -3
pixi run mypy --ignore-missing-imports --explicit-package-bases --python-version 3.10 tools/ 2>&1 | tail -3
pixi run mypy --ignore-missing-imports --explicit-package-bases --python-version 3.10 examples/ 2>&1 | tail -3
```

Watch for **duplicate module** errors in directories with hyphenated subdirectory names
(e.g., `alexnet-cifar10/`, `paper-scaffold/`). These are **not suppressible** via overrides —
exclude those directories from the hook pattern.

### Step 2: Identify which config file mypy auto-discovers

```bash
# mypy.ini takes precedence over pyproject.toml
ls mypy.ini .mypy.ini setup.cfg pyproject.toml 2>/dev/null
```

The `mirrors-mypy` pre-commit hook runs in an **isolated virtualenv** but still auto-discovers
`mypy.ini` from the repo root (CWD). It does NOT auto-discover `pyproject.toml` unless
`--config-file pyproject.toml` is explicitly passed.

### Step 3: Add baseline suppression in mypy.ini (NOT pyproject.toml)

```ini
# Baseline suppression for tests/, tools/ — fix incrementally (see #NNNN)
[mypy-tests.*]
ignore_errors = True

[mypy-tools.*]
ignore_errors = True
```

Add transitive import targets too (e.g., if `tests/notebooks/` imports from `notebooks/utils/`):

```ini
[mypy-notebooks.*]
ignore_errors = True
```

### Step 4: Widen the hook files pattern

```yaml
# .pre-commit-config.yaml
- id: mypy
  files: ^(scripts|tests|tools)/.*\.py$  # was: ^scripts/.*\.py$
  args: [--ignore-missing-imports, --no-strict-optional, --explicit-package-bases, --python-version, "3.10"]
```

### Step 5: Fix genuine errors in newly covered files

For small numbers of real errors (e.g., `callable` used as a type annotation — which is invalid):

```python
# Before (invalid):
from typing import Optional
validator: Optional[callable] = None

# After (correct):
from typing import Callable, Optional
validator: Optional[Callable[[str], tuple[bool, str]]] = None
```

### Step 6: Verify

```bash
pixi run pre-commit run mypy --all-files
pixi run pre-commit run --all-files
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `[[tool.mypy.overrides]]` in `pyproject.toml` | Added `ignore_errors = true` for `tests.*`, `tools.*` | `mirrors-mypy` hook virtualenv doesn't auto-load `pyproject.toml` | Use `mypy.ini` for overrides — it's auto-discovered by mypy regardless of invocation context |
| `--config-file pyproject.toml` in hook args | Added to force config loading | `pyproject.toml` has `disallow_untyped_defs = true` which broke `scripts/` (269 new errors) | Config files have stricter settings than hook standalone args; mixing them causes regressions |
| Including `examples/` in hook pattern | Added `examples` to `files:` regex | Directories like `alexnet-cifar10/` are not valid Python identifiers — duplicate module fatal error | Hyphenated directory names are incompatible with mypy module resolution; exclude them entirely |
| `[mymy-tools.*]` override matching `tools/paper-scaffold/prompts.py` | Expected override to suppress errors in `paper-scaffold` subdir | `paper-scaffold` contains a hyphen — not a valid Python package name — so mypy resolves the module as top-level `prompts`, not `tools.paper-scaffold.prompts` | Fix the actual errors in hyphenated-dir files rather than relying on module-path overrides |
| Forgetting transitive imports | Added `ignore_errors` only for directly covered dirs | `tests/notebooks/test_utils.py` imports `notebooks.utils` — mypy followed the import and reported errors in `notebooks/utils/*.py` | Always check which modules are imported transitively; add overrides for those too |

## Results & Parameters

### Final `.pre-commit-config.yaml` diff

```yaml
- id: mypy
  files: ^(scripts|tests|tools)/.*\.py$   # Extended from ^scripts/.*\.py$
  args: [--ignore-missing-imports, --no-strict-optional, --explicit-package-bases, --python-version, "3.10"]
  additional_dependencies: [types-PyYAML]
```

### Final `mypy.ini` additions

```ini
# Baseline suppression for tests/, tools/, notebooks/ — fix incrementally
[mypy-tests.*]
ignore_errors = True

[mypy-tools.*]
ignore_errors = True

[mypy-notebooks.*]
ignore_errors = True
```

### Key facts about mypy config file discovery

- **Search order**: `mypy.ini` > `.mypy.ini` > `setup.cfg` > `pyproject.toml`
- `mirrors-mypy` pre-commit hook: auto-discovers `mypy.ini` from repo root ✅
- `mirrors-mypy` pre-commit hook: does NOT auto-discover `pyproject.toml` without `--config-file` ❌
- `[mypy-module.*]` patterns only match when the module path is a valid Python identifier path
- Hyphenated directory names (`paper-scaffold/`) prevent proper module path construction

### Detecting transitive import issues

```bash
# Find which tested files import from outside the covered dirs
grep -r "^from\|^import" tests/ | grep -v "^tests/" | grep "notebooks\|examples"
```
