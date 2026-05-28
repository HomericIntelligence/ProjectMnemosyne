---
name: python-version-gated-stdlib-import-guard
description: "Guard stdlib modules that were added in a later Python version so that code remains importable on older versions in the test matrix. Use when: (1) CI matrix includes Python 3.10 and code does a bare import of a 3.11+ stdlib module (tomllib, ExceptionGroup, etc.), (2) test file collection fails with ModuleNotFoundError for a stdlib module on the lowest Python in the matrix, (3) adding tomllib usage and the repo supports Python <3.11, (4) any bare stdlib import causes collection errors on the minimum supported Python version."
category: tooling
date: 2026-05-28
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [python, stdlib, tomllib, tomli, version-guard, ci, import, 3.10, 3.11, compatibility]
---

# Python Version-Gated stdlib Import Guard

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-28 |
| **Objective** | Keep test/source files importable on the minimum Python version in the CI matrix when they use a stdlib module that was added in a newer Python version |
| **Outcome** | Successful. CI test collection on Python 3.10 fixed; 2590 tests pass. Verified in ProjectHephaestus PR #657. |
| **Verification** | verified-ci |

## When to Use

- A CI test matrix includes Python 3.10 and a source or test file does a bare `import tomllib` (stdlib only since Python 3.11).
- `pytest` collection fails with `ModuleNotFoundError: No module named 'tomllib'` on the lowest Python in the matrix.
- Adding TOML-parsing to a module that must support Python <3.11.
- Any bare stdlib import (`ExceptionGroup`, `tomllib`, `importlib.resources` new API) causes failures on the minimum supported Python version.

## Verified Workflow

### Quick Reference

```python
# Standard pattern — use sys.version_info guard + backport package fallback
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[no-redef]
```

```toml
# pyproject.toml — declare the backport as a conditional dependency
[project]
dependencies = [
    "tomli; python_version < '3.11'",
]
```

```toml
# pixi.toml — add backport to deps for older-Python environments
[dependencies]
tomli = { version = ">=2.0", python = "<3.11" }
```

```bash
# Grep for all unguarded bare stdlib imports before patching
grep -rn "^import tomllib" hephaestus/ scripts/ tests/
# Expected: zero hits after the fix
```

### Detailed Steps

#### Fixing a bare tomllib import for Python 3.10 compatibility

1. Grep for all occurrences: `grep -rn "^import tomllib" hephaestus/ scripts/ tests/`
2. For each file, replace:

   ```python
   # BEFORE (fails on Python 3.10)
   import tomllib

   # AFTER
   import sys
   if sys.version_info >= (3, 11):
       import tomllib
   else:
       import tomli as tomllib  # type: ignore[no-redef]
   ```

3. Add `tomli` as a conditional dependency in `pyproject.toml`:

   ```toml
   [project]
   dependencies = [
       "tomli; python_version < '3.11'",
   ]
   ```

4. If pixi is used, add to `pixi.toml`:

   ```toml
   [dependencies]
   tomli = { version = ">=2.0", python = "<3.11" }
   ```

5. Run `pixi run pytest tests/unit` locally and confirm collection succeeds.
6. If mypy runs in CI on 3.11+ and flags the redefinition, add `# type: ignore[no-redef, unused-ignore]` on the `import tomli as tomllib` line.

#### General pattern for any version-gated stdlib module

```python
import sys

if sys.version_info >= (MAJOR, MINOR):
    from stdlib_module import something
else:
    from backport_package import something  # type: ignore[no-redef]
```

Known version-gated stdlib modules and their backports:

| Module | Added in | Backport package |
|--------|----------|-----------------|
| `tomllib` | 3.11 | `tomli` |
| `ExceptionGroup` | 3.11 | `exceptiongroup` |
| `importlib.resources` (new API) | 3.9 | `importlib_resources` |
| `zoneinfo` | 3.9 | `backports.zoneinfo` |
| `graphlib` | 3.9 | `graphlib_backport` |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Bare `import tomllib` in test file | Used stdlib tomllib directly assuming CI matrix was 3.11+ | Matrix also ran Python 3.10; collection failed with `ModuleNotFoundError` | Always check the lowest Python version in the CI matrix before using stdlib modules added in newer versions |
| `try: import tomllib except ImportError: import tomli as tomllib` | Used try/except instead of sys.version_info guard | Works at runtime but mypy cannot statically narrow the type; false positive on 3.11+ | Use `sys.version_info >= (3, 11)` guard — mypy understands version checks as a type narrowing predicate |
| Skip adding `tomli` as dependency, assume pre-installed | Did not add `tomli; python_version < '3.11'` to `pyproject.toml` | `tomli` not available in fresh CI environment; `ModuleNotFoundError: No module named 'tomli'` | Always declare backport as conditional dependency in both `pyproject.toml` and `pixi.toml` |

## Results & Parameters

### Expected output after fix

```
$ pixi run pytest tests/unit -q --tb=no
...
2590 passed, 2 skipped in 168.87s
```

Test collection must succeed on both Python 3.10 and 3.11+ matrix legs.

### Type-ignore comment pattern

When mypy runs on Python 3.11+ and sees both branches of the import guard:

```python
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[no-redef, unused-ignore]
```

The `unused-ignore` suppress is needed on 3.11+ where mypy knows the `else` branch is
unreachable and would otherwise warn that `# type: ignore[no-redef]` is unused.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #657 — fix broken main CI | tests/unit/ci/test_bandit_config.py, pyproject.toml, pixi.toml |
