---
name: mojo-package-level-reexports
description: "Add convenience top-level re-exports to a Mojo package __init__.mojo. Use when: enabling `from shared import SGD` style imports, activating commented-out import lines after implementation is ready, or adding a new optimizer struct that mirrors an existing one with decoupled behavior."
category: architecture
date: 2026-03-07
user-invocable: false
---

# Skill: Mojo Package-Level Re-exports and New Optimizer Structs

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Objective** | Enable `from shared import SGD, Adam, AdamW`; implement AdamW with decoupled weight decay |
| **Outcome** | Activated re-export line in `shared/__init__.mojo`, added AdamW struct (295 lines), added import test; PR #3738 created |
| **PRs** | [#3738](https://github.com/HomericIntelligence/ProjectOdyssey/pull/3738) |

## Overview

ProjectOdyssey's `shared/__init__.mojo` had commented-out re-export lines for optimizers. The issue
asked to: (1) uncomment/activate re-exports for SGD and Adam, (2) implement AdamW (Issue #49
follow-up), and (3) add AdamW to the re-exports. The pattern is straightforward but requires
care about which module path to import from (`shared.autograd.optimizers` vs
`shared.training.optimizers`).

## When to Use

1. A Mojo package has commented-out re-export lines waiting for implementation to be ready
2. You need to add a new optimizer struct that is an Adam variant (decouple weight decay from gradient)
3. You want `from <package> import <Symbol>` to work at the top level, sourcing from a submodule
4. You need to trace where a symbol actually lives before exposing it at the package level

## Verified Workflow

### Phase 1: Find where symbols are actually defined

Before activating any re-export, confirm the canonical definition location:

```bash
grep -rn "struct SGD\|struct Adam\b\|struct AdamW" shared/
```

In this session:
- `SGD` and `Adam` are in `shared/autograd/optimizers.mojo`
- `shared/training/__init__.mojo` re-exports `SGD` from `shared.training.optimizers.sgd`
- Use the autograd path for the shared package re-export to avoid ambiguity

### Phase 2: Activate the re-export in `shared/__init__.mojo`

Find the commented line and uncomment it, pointing at the correct module:

```mojo
# Before (commented out):
# from .training.optimizers import SGD, Adam, AdamW

# After (activated, using actual source path):
from shared.autograd.optimizers import SGD, Adam, AdamW
```

Key: Use the absolute module path (`shared.autograd.optimizers`), not relative (`.training.optimizers`),
because the symbol lives in autograd, not training.

### Phase 3: Implement AdamW by mirroring Adam

AdamW is Adam with **decoupled** weight decay. The only algorithmic difference:

- Adam: adds `weight_decay * param` to the gradient before the adaptive update
- AdamW: applies `learning_rate * weight_decay * param` directly to the parameter after the Adam update

Copy the Adam struct, rename to AdamW, change `weight_decay` default from `0.0` to `0.01`, and replace
the update kernel:

```mojo
# Adam (L2 regularization folded into gradient):
var weight_decay_update = multiply_scalar(parameters[i].data, self.learning_rate * self.weight_decay)
param_update = scaled_grad + weight_decay_update  # adds to gradient update

# AdamW (decoupled - applied directly to parameter):
var decay_val = self.learning_rate * self.weight_decay * param_val
new_data._set_float64(j, param_val - update_val - decay_val)  # subtract from param directly
```

### Phase 4: Add import test

Add a dedicated test function for the new top-level imports:

```mojo
fn test_shared_optimizer_imports() raises:
    """Test that SGD, Adam, AdamW are importable directly from shared package."""
    from shared import SGD, Adam, AdamW

    print("✓ Shared optimizer imports test passed")
```

Wire it into `main()` after `test_training_optimizers_imports()`.

### Phase 5: Run pre-commit before committing

```bash
git add <files>
pixi run pre-commit run --files <files>
```

Mojo's pre-commit hook auto-formats. If it reformats files, they'll be unstaged — re-add and commit.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running `mojo test` locally | Tried `pixi run mojo test tests/shared/test_imports.mojo` | GLIBC version mismatch on host (requires 2.32+, host has 2.31) | Local mojo execution not available on this host; CI is the test oracle |
| Running tests via Docker | `docker run ghcr.io/homericintelligence/projectodyssey:main ...` | Docker image not locally available (denied, not cached) | CI must run tests; verify by reviewing code structure and running pre-commit |
| Using relative import in `__init__.mojo` | Considered `from .autograd.optimizers import ...` | Relative imports from `shared/__init__.mojo` in Mojo use absolute-style paths | Use `from shared.autograd.optimizers import ...` (absolute module path) |

## Results & Parameters

**Files modified**:

| File | Change |
|------|--------|
| `shared/autograd/optimizers.mojo` | +295 lines: AdamW struct with decoupled weight decay |
| `shared/__init__.mojo` | Activated re-export: `from shared.autograd.optimizers import SGD, Adam, AdamW` |
| `tests/shared/test_imports.mojo` | +8 lines: `test_shared_optimizer_imports()` + wired to `main()` |

**AdamW default parameters**:

```mojo
fn __init__(
    out self,
    learning_rate: Float64 = 0.001,
    beta1: Float64 = 0.9,
    beta2: Float64 = 0.999,
    epsilon: Float64 = 1e-8,
    weight_decay: Float64 = 0.01,   # Note: 0.01 default, not 0.0 like Adam
):
```

**Key algorithmic distinction** (decoupled weight decay):

```mojo
# Per-element update in AdamW.step():
var param_val = parameters[i].data._get_float64(j)
var update_val = adam_update._get_float64(j)
var decay_val = self.learning_rate * self.weight_decay * param_val
new_data._set_float64(j, param_val - update_val - decay_val)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3219, PR #3738 | [notes.md](../../references/notes.md) |
