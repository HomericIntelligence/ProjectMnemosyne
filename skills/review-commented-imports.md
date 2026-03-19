---
name: review-commented-imports
description: 'Review and resolve commented-out imports in module init files by auditing
  which are implemented, misnamed, or pending. Use when: cleaning up Mojo/Python __init__
  files with placeholder NOTEs, auditing API surface post-implementation, or documenting
  name mismatches between planned and actual symbols.'
category: documentation
date: 2026-03-04
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Objective** | Audit commented-out imports in a module `__init__` file to determine status of each |
| **Language** | Mojo (applies to Python too) |
| **Trigger** | Module init has `# NOTE: commented out until implementation` blocks |
| **Output** | Uncommented implemented imports, annotated pending imports, updated module docstring |

## When to Use

- A `__init__.mojo` or `__init__.py` has large blocks of commented imports with `NOTE:` markers
- Post-implementation cleanup: verifying which symbols are now available
- API surface audit: identifying planned names that were implemented under different names
- Documenting language limitations (e.g., Mojo's lack of `__all__` support)

## Verified Workflow

### Step 1: Read the init file

Read the target file to understand the full import structure and NOTE comments.

### Step 2: Audit submodule exports in parallel

For each commented import group, grep the corresponding submodule:

```bash
# Check if struct/fn exists with exact name
grep -rn "^struct Linear\b\|^fn relu\b" shared/core/

# Check what the submodule's __init__ actually exports
grep -n "^from\|^struct\|^fn" shared/core/__init__.mojo | head -30

# Find actual name if known-alias exists
grep -rn "^struct Conv" shared/core/layers/
```

### Step 3: Categorize each import

For each commented import, determine:

| Status | Action |
|--------|--------|
| Implemented with matching name | Uncomment with corrected path |
| Implemented under different name | Add comment mapping old→new name |
| Not yet implemented | Keep commented, add `# NOT YET IMPLEMENTED (see Issue #N)` |
| Wrong module path | Fix path typo (e.g., `activations` → `activation`) |
| Language limitation | Document in module docstring |

### Step 4: Update module docstring

Move language-limitation NOTEs from inline comments into the module docstring:

```mojo
"""
...
Note:
    Mojo v0.26.1+ does not support ``__all__`` module-level assignments.
    All public symbols are automatically exported. The convenience re-exports
    below are uncommented as implementations reach stable naming conventions.

    Name mismatches from original plan:
    - Conv2D -> Conv2dLayer (shared.core.layers.conv2d)
    - ReLU -> ReLULayer (shared.core.layers.relu)

    Not yet implemented (see Issue #49):
    - Sequential, MaxPool2D, AdamW
"""
```

### Step 5: Apply changes

For implemented imports, uncomment and fix paths:

```mojo
# Before:
# from .core.activations import relu, sigmoid, tanh, softmax

# After (fixed module name typo):
from shared.core.activation import relu, sigmoid, tanh, softmax
```

For unimplemented imports, annotate:

```mojo
# NOT YET IMPLEMENTED (see Issue #49): Tensor, zeros, ones, randn
# Use: from shared.core.extensor import ExTensor
```

### Step 6: Remove redundant comment blocks

If a `# Public API` or `# NOTE:` comment block restates what is now in the docstring,
remove it to avoid duplication.

### Step 7: Commit to feature branch

Use `SKIP=mojo-format` if the Mojo formatter cannot run due to GLIBC incompatibility
on the local host (will run correctly in CI via Docker):

```bash
SKIP=mojo-format git commit -m "fix(shared): review commented-out imports in __init__.mojo

- Uncomment implemented imports: Linear, relu/sigmoid/tanh/softmax, Module, ...
- Fix module path typo: 'activations' -> 'activation'
- Annotate unimplemented imports with Issue #N references
- Document __all__ Mojo limitation and name mismatches in module docstring
- Remove redundant NOTE block from Public API section

Closes #NNNN"
```

## Key Patterns Discovered

### Worktree vs Main Repo File Paths

When working in a git worktree, always edit files in the **worktree directory**, not the
main repo directory. They are separate working trees even though they share the git repo:

```
/repo/                          # main checkout (on branch 'main')
/repo/.worktrees/issue-N/       # worktree checkout (on branch 'N-feature')
```

Editing `/repo/shared/__init__.mojo` affects `main`, not the feature branch.
Edit `/repo/.worktrees/issue-N/shared/__init__.mojo` instead.

### Committing from a Worktree

```bash
# Stage and commit from within the worktree:
git -C /repo/.worktrees/issue-N add shared/__init__.mojo
git -C /repo/.worktrees/issue-N commit -m "..."
git -C /repo/.worktrees/issue-N push -u origin N-feature
```

### Mojo Module Path Conventions

Mojo uses absolute paths from the project root, not relative imports:
- Use `from shared.core.activation import relu` (absolute)
- NOT `from .core.activations import relu` (relative, wrong module name)

### GLIBC Incompatibility Skip

When `mojo-format` hook fails due to GLIBC version mismatch on the host:

```bash
SKIP=mojo-format git commit -m "..."
```

This is valid since the hook runs correctly in CI Docker containers where GLIBC >= 2.34.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Edit main repo file | Edited `/repo/shared/__init__.mojo` directly | File is tracked by `main` branch, not the worktree branch `3093-auto-impl` | Always edit the worktree copy at `/repo/.worktrees/issue-N/shared/__init__.mojo` |
| Commit from main repo | `git add shared/__init__.mojo` from `/repo/` | Branch `3093-auto-impl` is checked out in worktree, not main repo | Use `git -C /repo/.worktrees/issue-N` prefix for all git commands |
| Relative import paths | Used `from .core.activation import ...` | Mojo `__init__` files require absolute import paths | Always use `from shared.core.X import Y` in Mojo init files |

## Results & Parameters

### Session: Issue #3093 - Review commented-out imports in shared/__init__.mojo

**File audited**: `shared/__init__.mojo` (153 lines → 127 lines)

**Imports uncommented** (9 symbols):
- `Linear` from `shared.core.layers.linear`
- `relu, sigmoid, tanh, softmax` from `shared.core.activation` (fixed path typo)
- `Module` from `shared.core.module`
- `StepLR, CosineAnnealingLR` from `shared.training.schedulers`
- `EarlyStopping, ModelCheckpoint` from `shared.training.callbacks`
- `Logger` from `shared.utils.logging`
- `plot_training_curves` from `shared.utils.visualization`

**Imports left commented with tracking** (Issue #49):
- `Tensor/zeros/ones/randn` → `ExTensor`
- `Conv2D/ReLU/Dropout` → `Conv2dLayer/ReLULayer/DropoutLayer`
- `Sequential, MaxPool2D, Flatten, AdamW`
- `train_epoch, validate_epoch`
- `TensorDataset, ImageDataset, DataLoader, ToTensor`

**PR**: https://github.com/HomericIntelligence/ProjectOdyssey/pull/3217
