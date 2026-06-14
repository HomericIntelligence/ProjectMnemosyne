---
name: python-automation-god-package-shim-antipattern
description: "The import * shim strategy for Python package reorganization is fatally flawed unless all modules define __all__. Use when: (1) planning to move Python modules to sub-packages with backward-compat shims, (2) considering wildcard imports as a migration strategy, (3) auditing a large Python package for reorganization."
category: architecture
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [python, import, shim, migration, god-package, __all__, wildcard-import, refactoring]
---

# Python Automation God-Package: Import * Shim Antipattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-13 |
| **Objective** | Plan reorganization of a large Python automation package (50 modules) using backward-compat shims |
| **Outcome** | Proposed shim strategy was rejected (NOGO) — fatally flawed without universal `__all__` coverage |
| **Verification** | unverified |

## When to Use

- Planning to move Python modules to sub-packages while keeping backward-compat shims
- Considering `from subpackage.module import *` as a migration strategy
- Auditing `__all__` coverage before any wildcard-import reorganization
- Claiming that `git mv` requires "no logic changes" for Python modules
- Evaluating reorganization of any Python package with 20+ modules

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# Audit __all__ coverage before any import * migration
grep -l '__all__' hephaestus/automation/*.py | wc -l   # how many define it
grep -L '__all__' hephaestus/automation/*.py           # which ones don't (these CANNOT use import *)

# Audit relative imports before moving modules (all need rewriting after a move)
grep -rn 'from \.' hephaestus/automation/*.py | wc -l  # count; all must be updated after move

# Count actual files on disk (don't trust stale audit figures)
ls hephaestus/automation/*.py | wc -l

# Check for the correct pattern: explicit re-exports (see prompts/__init__.py)
cat hephaestus/automation/prompts/__init__.py  # lists all 28 symbols explicitly — the right approach
```

### Detailed Steps

1. **Audit `__all__` coverage first** — run `grep -L '__all__' <package>/*.py` to identify modules that do NOT define `__all__`. Any module without `__all__` cannot be used as a source for `from X import *` shims — private symbols will be silently dropped and `from X import __all__` will crash with `ImportError`.

2. **If `__all__` coverage is below 100%, abandon the wildcard-shim strategy** — in large automation packages, expect <25% coverage. The correct alternative is explicit per-symbol re-exports (enumerate each public symbol in the shim `__init__.py`).

3. **Audit relative imports before claiming `git mv` is "no logic change"** — run `grep -rn 'from \.' <package>/*.py`. Every relative import (`from .sibling`, `from ..utils`) breaks immediately after a module is moved to a different directory. There is no such thing as a logic-free Python module move when relative imports are present.

4. **Use the explicit re-export pattern instead** — see `hephaestus/automation/prompts/__init__.py` as the correct template: it lists all 28 public symbols explicitly. This is verbose but correct and type-checker-friendly.

5. **Consider `__getattr__`-based lazy loading** — for large packages, the existing `automation/__init__.py` lazy-loader pattern (`__getattr__` + `_LAZY_EXPORTS` dict) is the correct approach for deferred imports without wildcard pollution.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Wildcard shims | `from new.location.module import *` shim files in old locations | Modules without `__all__` export nothing private; `from X import __all__` crashes with ImportError | Always enumerate symbols explicitly; `import *` is not a migration tool |
| "No logic changes" claim | `git mv` + shim assumed to preserve all imports | Relative imports in moved modules break immediately (`from .sibling` → `from ..sibling`) | Audit every relative import before claiming a move is logic-free |
| Stale file count | Used audit figure of 52 files | Actual on-disk count was 50; audit was dated | Always `ls hephaestus/automation/*.py \| wc -l` before referencing file counts |
| 8 sub-package decomposition | Proposed physical split into core/, runners/, drivers/, etc. | ADR-0001 explicitly rejected physical decomposition as the remedy; install-boundary was the prescribed fix | Read the cited ADR before proposing structural reorganization |

## Results & Parameters

```bash
# ProjectHephaestus hephaestus/automation/ — actual audit (2026-06-13)
ls hephaestus/automation/*.py | wc -l
# → 50 files (audit claimed 52 — stale)

grep -l '__all__' hephaestus/automation/*.py | wc -l
# → ~10 files define __all__ (20% coverage)

grep -L '__all__' hephaestus/automation/*.py | wc -l
# → ~40 files DO NOT define __all__ (80% — cannot use import *)

grep -rn 'from \.' hephaestus/automation/*.py | wc -l
# → hundreds of relative imports; all break after any module move

# Correct pattern example:
# hephaestus/automation/prompts/__init__.py explicitly lists 28 symbols
# This is the template to follow for backward-compat re-exports

# Correct lazy-load pattern:
# hephaestus/automation/__init__.py uses __getattr__ + _LAZY_EXPORTS dict
# This avoids wildcard pollution while supporting lazy import
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1177 planning round 1 (NOGO) | 50-module automation package; <20% __all__ coverage; hundreds of relative imports |
