---
name: python-mypy-explicit-reexport-pattern
description: "mypy with implicit_reexport=false requires `from X import Y as Y` (explicit re-export) for symbols re-exported from a module. Use when: (1) moving a symbol to a leaf module and re-exporting for backward compatibility, (2) mypy raises 'does not explicitly export attribute X', (3) maintaining mock.patch-compatible namespace bindings after a module refactor."
category: architecture
date: 2026-04-29
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [mypy, python, reexport, implicit_reexport, mock, patch, backward-compatibility]
---

# Python mypy Explicit Re-export Pattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-29 |
| **Objective** | Re-export a symbol from a module for backward compatibility after moving it to a leaf module, while satisfying mypy's `implicit_reexport = false` strict setting |
| **Outcome** | Success — `from X import Y as Y` satisfies mypy and keeps `mock.patch` bindings working |
| **Verification** | verified-local — mypy passed, all tests passed (PR #308 ProjectHephaestus) |

## When to Use

- mypy raises `Module "pkg.module" does not explicitly export attribute "X"` after you wrote `from other.module import X`
- You moved a symbol to a leaf module and need backward-compatible re-exports in the original location (e.g., 30+ `@patch` decorators patching the old path)
- Your `pyproject.toml` has `implicit_reexport = false` under `[tool.mypy]`
- You want to clearly signal that an import in a module is part of its *public API* (not just an implementation detail)

## Verified Workflow

### Quick Reference

```python
# CORRECT — explicit re-export (mypy sees this as intentional public API):
from hephaestus.github.gh_subprocess import _gh_call as _gh_call

# WRONG — implicit re-export (fails with implicit_reexport = false):
from hephaestus.github.gh_subprocess import _gh_call

# Also works — re-export under a new public name:
from hephaestus.github.gh_subprocess import _gh_call as gh_call
```

```toml
# The pyproject.toml setting that triggers this requirement:
[tool.mypy]
implicit_reexport = false
```

### Detailed Steps

1. **Identify the error**: mypy reports `Module "pkg.module" does not explicitly export attribute "X"` when another file does `from pkg.module import X` and `pkg/module.py` got `X` via a plain `from other import X`.

2. **Locate the re-exporting module**: Find the file that has the plain `from leaf_module import symbol` that mypy is complaining about.

3. **Apply the explicit re-export pattern**: Change:
   ```python
   # Before (implicit — mypy rejects under implicit_reexport = false):
   from hephaestus.github.gh_subprocess import _gh_call
   ```
   To:
   ```python
   # After (explicit — mypy accepts this as intentional re-export):
   from hephaestus.github.gh_subprocess import _gh_call as _gh_call
   ```

4. **Verify mock.patch still works**: `mock.patch("pkg.module._gh_call")` patches the name `_gh_call` in `pkg.module`'s namespace. With the explicit re-export, `_gh_call` is bound in that namespace — `mock.patch` patches that binding. Tests calling functions in `pkg/module.py` that call `_gh_call` see the patched version because Python looks up `_gh_call` in the module's globals at call time.

5. **Run mypy and tests**:
   ```bash
   pixi run mypy
   pixi run pytest tests/
   ```

6. **Optionally add to `__all__`** if you want `from pkg.module import *` to expose the symbol too (separate concern from mypy re-export):
   ```python
   __all__ = ["_gh_call"]  # or the public name if renamed
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Plain import | `from hephaestus.github.gh_subprocess import _gh_call` | mypy raises "Module does not explicitly export attribute '_gh_call'" when `implicit_reexport = false` | The plain `from X import Y` form is treated as an implementation detail by mypy, not a public re-export |
| `__all__` workaround | Adding `"_gh_call"` to `__all__` in the re-exporting module without changing the import | `__all__` controls `from module import *` behavior; mypy still requires the `as Y` form for the import statement itself | `__all__` and explicit re-export are independent mechanisms — both may be needed for full correctness |

## Results & Parameters

**Config that triggers this behavior** (`pyproject.toml`):
```toml
[tool.mypy]
implicit_reexport = false
```

**The canonical pattern** (copy-paste ready):
```python
# In the backward-compatibility shim module:
# Move: symbol was in this_module.py, moved to new_location.py
# Re-export for backward compat (preserves mock.patch paths):
from package.new_location import MySymbol as MySymbol  # noqa: PLC0414  # explicit re-export
```

**Why `as Y` with the same name works**: The `import Y as Y` form is recognized by mypy as an explicit declaration that `Y` is intended to be part of the module's public interface. The PEP 484 specification for `implicit_reexport = false` defines this as the canonical opt-in signal.

**Why mock.patch is unaffected**: Python's `mock.patch("a.b.Symbol")` replaces the attribute named `Symbol` in module `a.b`'s `__dict__`. The explicit re-export `from x import Symbol as Symbol` places `Symbol` in `a.b.__dict__` — identical to a plain `from x import Symbol`. The difference only exists at the static analysis level (mypy), not at runtime.

**Optional lint suppression** (if ruff flags redundant alias):
```python
from package.new_location import MySymbol as MySymbol  # noqa: PLC0414
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #308 — moved `_gh_call` to `hephaestus/github/gh_subprocess.py`, re-exported from `hephaestus/automation/github_api.py` for 30+ `@patch` backward compatibility | verified-local: mypy pass + all tests pass |
