---
name: mojo-package-level-reexports
description: 'Add convenience top-level re-exports to a Mojo package __init__.mojo.
  Use when: enabling `from shared import X` style imports, activating commented-out
  import lines after implementation is ready, adding optimizer structs (AdaGrad/RMSprop/AdamW),
  or extending an existing re-export group with new symbols.'
category: architecture
date: 2026-03-07
version: 2.0.0
user-invocable: false
---
# Skill: Mojo Package-Level Re-exports and New Optimizer Structs

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 (updated 2026-03-15) |
| **Objective** | Enable `from shared import SGD, Adam, AdamW, AdaGrad, RMSprop` at top-level package |
| **Outcome** | Activated/extended re-export line in `shared/__init__.mojo`; all 5 optimizers exposed |
| **PRs** | [#3738](https://github.com/HomericIntelligence/ProjectOdyssey/pull/3738) (SGD/Adam/AdamW), [#4785](https://github.com/HomericIntelligence/ProjectOdyssey/pull/4785) (AdaGrad/RMSprop) |

## Overview

ProjectOdyssey's `shared/__init__.mojo` had commented-out re-export lines for optimizers. Two
sequential issues activated and extended these:

- **Issue #3219 / PR #3738**: Activate re-exports for SGD, Adam; implement and add AdamW
- **Issue #3745 / PR #4785**: Add AdaGrad and RMSprop to the same re-export line

The pattern is straightforward but requires care: (1) identify the canonical defining module,
(2) use an absolute import path, (3) add all symbols from a group in one line, (4) verify
commented-out blocks don't point to the wrong submodule.

## When to Use

1. A Mojo package has commented-out re-export lines waiting for implementation to be ready
2. You need to add a new optimizer struct (AdamW, AdaGrad, RMSprop) to the top-level API
3. You want `from shared import X` to work at the top level, sourcing from a submodule
4. A follow-up issue asks to extend an existing optimizer re-export with additional symbols
5. You need to trace where a symbol actually lives before exposing it at the package level
6. An import audit (e.g. Issue #49) identifies symbols only accessible via full path like `from shared.data.transforms import Normalize`

## Verified Workflow

### Quick Reference

| Step | Action | Command |
|------|--------|---------|
| 1 | Find defining module | `grep -rn "^struct AdaGrad" shared/` |
| 2 | Check intermediate `__init__` | `grep -n "AdaGrad" shared/autograd/__init__.mojo` |
| 3 | Audit active imports in top-level | `grep -n "^from" shared/__init__.mojo` |
| 4 | Check commented blocks point to right module | `grep -n "# from" shared/__init__.mojo` |
| 5 | Add/extend active import | Edit `shared/__init__.mojo` |
| 6 | Update API table comment | Update `# Public API Table` block |
| 7 | Write test | `tests/shared/autograd/test_top_level_optimizer_imports.mojo` |
| 8 | Verify with grep | `grep -n "AdaGrad\|RMSprop" shared/__init__.mojo` |

### Phase 1: Find where symbols are actually defined

Before activating any re-export, confirm the canonical definition location:

```bash
grep -rn "^struct SGD\|^struct Adam\b\|^struct AdaGrad\|^struct RMSprop" shared/
```

In this project:
- All 5 optimizers (`SGD`, `Adam`, `AdamW`, `AdaGrad`, `RMSprop`) live in `shared/autograd/optimizers.mojo`
- `shared/autograd/__init__.mojo` already re-exports them (line 143)
- `shared/training/__init__.mojo` re-exports only `SGD` from a different path

### Phase 2: Audit `shared/__init__.mojo` BEFORE making changes

```bash
grep -n "^from" shared/__init__.mojo    # active imports
grep -n "# from" shared/__init__.mojo   # commented-out (may be stale/wrong)
```

**Critical lesson (Issue #3745)**: The commented-out block:

```mojo
# from .training.optimizers import SGD, Adam, AdamW
```

looks like the prior re-export. But it points to `training.optimizers`, NOT to
`shared.autograd.optimizers` where the symbols actually live. Do not extend this block.

**Always check which submodule actually defines the symbol** before extending a commented block.

### Phase 3: Add or extend the active import

If no active optimizer import exists (Issue #3745 case), add one:

```mojo
# Training optimizers - available at top-level shared package
from shared.autograd.optimizers import SGD, Adam, AdamW, AdaGrad, RMSprop
```

If an active import already exists (prior PR had activated it), extend it to add missing symbols:

```mojo
# Before:
from shared.autograd.optimizers import SGD, Adam, AdamW
# After:
from shared.autograd.optimizers import SGD, Adam, AdamW, AdaGrad, RMSprop
```

**Key rules**:

- Use the **absolute module path** (`shared.autograd.optimizers`), not relative (`.autograd.optimizers`)
- Import ALL symbols from the group in a single line for consistency
- Do NOT import from the intermediate `__init__.mojo` (`from shared.autograd import AdaGrad`) —
  this triggers the Mojo v0.26.1 re-export chain limitation

### Phase 4: Update the Public API table comment

Find the `# Public API Table` block in `shared/__init__.mojo` and add a row:

```mojo
# │ SGD, Adam, AdamW, AdaGrad,      │ shared.autograd.optimizers             │
# │   RMSprop                       │                                        │
```

Also update the prose comment:

```mojo
# Training - Optimizers: SGD, Adam, AdamW, AdaGrad, RMSprop (via autograd)
```

### Phase 5: Add import test

Create `tests/shared/autograd/test_top_level_optimizer_imports.mojo`
(or update `tests/shared/test_imports.mojo`):

```mojo
# ≤10 fn test_ functions per file
from shared import AdaGrad, RMSprop, SGD, Adam, AdamW

fn test_adagrad_top_level_import() raises:
    var opt = AdaGrad(learning_rate=0.01)
    assert_almost_equal(opt.get_lr(), 0.01, tolerance=1e-10)
    print("✓ AdaGrad top-level import test passed")

fn test_rmsprop_top_level_import() raises:
    var opt = RMSprop(learning_rate=0.001)
    assert_almost_equal(opt.get_lr(), 0.001, tolerance=1e-10)
    print("✓ RMSprop top-level import test passed")
```

Pattern: Import at module top-level then instantiate and call `get_lr()` to prove the import
is functional, not just parseable at compile time.

### Phase 6: Implement AdamW (if needed) by mirroring Adam

AdamW is Adam with **decoupled** weight decay. The only algorithmic difference:

- Adam: adds `weight_decay * param` to the gradient before the adaptive update
- AdamW: applies `learning_rate * weight_decay * param` directly to the parameter after the Adam update

```mojo
# Per-element update in AdamW.step():
var param_val = parameters[i].data._get_float64(j)
var update_val = adam_update._get_float64(j)
var decay_val = self.learning_rate * self.weight_decay * param_val
new_data._set_float64(j, param_val - update_val - decay_val)
```

## Variation: Non-Optimizer Re-exports (Data Transforms Pattern)

The same workflow applies to any symbol group, not just optimizers. Example: exposing `Normalize`
and `Compose` from `shared/data/transforms.mojo` at both `shared.data` and `shared`:

```mojo
# shared/data/__init__.mojo — add to relevant section
from shared.data.transforms import (
    Normalize,  # Normalize tensor values: (x - mean) / std
    Compose,    # Chain multiple transforms into a single transform
)

# shared/__init__.mojo — add after data transforms block
from shared.data import Normalize, Compose
```

Integration test pattern (two tests, one per import level):

```mojo
fn test_normalize_compose_from_shared_data() raises:
    from shared.data import Normalize, Compose
    var normalizer = Normalize(Float64(0.5), Float64(0.5))
    print("✓ Normalize and Compose importable from shared.data")

fn test_normalize_compose_from_shared() raises:
    from shared import Normalize, Compose
    var normalizer = Normalize(Float64(0.1307), Float64(0.3081))
    print("✓ Normalize and Compose importable from shared")
```

**Always verify the constructor signature** before writing test code:

```bash
grep -A 5 "fn __init__" shared/data/transforms.mojo | head -10
```

Minimal change set for a two-level re-export:

```text
shared/data/__init__.mojo                              — add leaf import
shared/__init__.mojo                                   — add package import
tests/shared/integration/test_packaging.mojo           — add 2 tests + register in main()
```

## Mojo v0.26.1 Re-Export Chain Limitation

This is the critical constraint driving this entire pattern:

```
shared/autograd/optimizers.mojo    → defines AdaGrad
shared/autograd/__init__.mojo      → imports AdaGrad from optimizers  ✓
shared/__init__.mojo               → does NOT import AdaGrad           ✗
```

Result: `from shared import AdaGrad` **fails** even though `from shared.autograd import AdaGrad` works.

**Fix**: `shared/__init__.mojo` must import directly from the defining module:

```mojo
from shared.autograd.optimizers import AdaGrad  # ✓ works
# NOT: from shared.autograd import AdaGrad       # ✗ re-export chain fails
```

This limitation is documented in `shared/__init__.mojo` under "Re-export Chain Limitation (#3754)".

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running `mojo test` locally | Tried `pixi run mojo test tests/shared/test_imports.mojo` | GLIBC version mismatch on host (requires 2.32+, host has 2.31) | Local mojo execution not available on this host; CI is the test oracle |
| Running tests via Docker | `docker run ghcr.io/homericintelligence/projectodyssey:main ...` | Docker image not locally available (denied, not cached) | CI must run tests; verify by reviewing code structure and running pre-commit |
| Using relative import in `__init__.mojo` | Considered `from .autograd.optimizers import ...` | Relative imports from `shared/__init__.mojo` in Mojo use absolute-style paths | Use `from shared.autograd.optimizers import ...` (absolute module path) |
| Importing via intermediate `__init__.mojo` | `from shared.autograd import AdaGrad` in `shared/__init__.mojo` | Triggers re-export chain limitation — Mojo v0.26.1 cannot chain re-exports through multiple `__init__.mojo` layers | Always import from the canonical defining module (`shared.autograd.optimizers`), not via an intermediate package |
| Extending the commented-out training import | Adding AdaGrad to `# from .training.optimizers import SGD, Adam, AdamW` | This references `training.optimizers` (wrong module for AdaGrad/RMSprop); also uses relative path syntax | Check which submodule actually defines the symbol with `grep -rn "^struct AdaGrad" shared/`; commented blocks may point to stale/wrong modules |
| Assuming commented-out block was the prior active import | Treating `# from .training.optimizers import SGD, Adam, AdamW` as the source of SGD/Adam/AdamW | That line was never active; the actual active import was `from shared.autograd.optimizers import SGD, Adam, AdamW` added in PR #3738 | Always audit with `grep -n "^from" shared/__init__.mojo` to find ACTIVE imports; commented lines are aspirational/stale |
| Using `Float32` in test instantiation | `var normalizer = Normalize(Float32(0.5), Float32(0.5))` | `Normalize.__init__` takes `Float64`, not `Float32` — compile error | Always grep the leaf module's `__init__` signature before writing test code: `grep -A 5 "fn __init__" shared/data/transforms.mojo` |
| Checking `just --list` for build recipes | Ran `just --list` to find build targets | `just` not installed in PATH | Use `pixi run mojo` directly or rely on CI |

## Results & Parameters

### Files Modified

| Session | File | Change |
|---------|------|--------|
| PR #3738 | `shared/autograd/optimizers.mojo` | +295 lines: AdamW struct |
| PR #3738 | `shared/__init__.mojo` | Activated: `from shared.autograd.optimizers import SGD, Adam, AdamW` |
| PR #3738 | `tests/shared/test_imports.mojo` | +8 lines: `test_shared_optimizer_imports()` |
| PR #4785 | `shared/__init__.mojo` | Extended: added `AdaGrad, RMSprop` to re-export line |
| PR #4785 | `tests/shared/autograd/test_top_level_optimizer_imports.mojo` | New: 5 test functions for all 5 optimizers |
| PR #4785 | `tests/shared/test_imports.mojo` | Updated to import from `shared` directly |

### Key Parameters

| Parameter | Value |
|-----------|-------|
| Mojo version | 0.26.1 (pinned in pixi.toml) |
| Import path | `shared.autograd.optimizers` (absolute, direct to defining module) |
| Test assertion | `assert_almost_equal(opt.get_lr(), expected, tolerance=1e-10)` |
| Test functions per file | ≤10 per file |
| AdamW weight_decay default | `0.01` (not `0.0` like Adam) |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3219, PR #3738 — SGD/Adam/AdamW | [notes.md](../../references/notes.md) |
| ProjectOdyssey | Issue #3745, PR #4785 — AdaGrad/RMSprop | [notes.md](../../references/notes.md) |
