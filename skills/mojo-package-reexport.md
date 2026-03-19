---
name: mojo-package-reexport
description: 'Add re-exports to Mojo package __init__.mojo files so symbols are accessible
  at higher-level import paths. Use when: an import audit reveals structs/fns only
  accessible via full path, or an issue asks to expose symbols at a parent package
  level.'
category: tooling
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | mojo-package-reexport |
| **Category** | tooling |
| **Complexity** | Low |
| **Files Changed** | 2-3 (`__init__.mojo` files + optional test) |
| **Risk** | Backward-compatible (additive only) |

## When to Use

- An import audit (e.g. Issue #49) identifies symbols only accessible via full path like `from shared.data.transforms import Normalize`
- An issue asks to add `Normalize` and `Compose` to `shared/data/__init__.mojo` and `shared/__init__.mojo`
- A struct is implemented in a leaf module but needs convenience access at a package boundary
- Follow-up issues from packaging or audit work (pattern: "re-export X from Y")

## Verified Workflow

### Step 1: Locate the struct in the leaf module

```bash
grep -n "^struct Normalize\|^struct Compose" shared/data/transforms.mojo
```

Confirm the exact struct name and constructor signature before writing test code.

### Step 2: Add to `shared/data/__init__.mojo`

Find the relevant section (e.g. "Transform Base Classes") and append:

```mojo
# Core transforms (most commonly used)
from shared.data.transforms import (
    Normalize,  # Normalize tensor values: (x - mean) / std
    Compose,  # Chain multiple transforms into a single transform
)
```

### Step 3: Add to `shared/__init__.mojo`

After the commented-out data transforms block, add a live import:

```mojo
# Data transforms (available now — re-exported from shared.data)
from shared.data import Normalize, Compose
```

Also update the docstring to show `from shared.data import Normalize, Compose` instead of the full path.

### Step 4: Add packaging integration tests

In `tests/shared/integration/test_packaging.mojo`, add two tests — one per import level:

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

Register both in `main()`.

### Step 5: Verify constructor types from the leaf module

**Critical**: check the actual field types (`Float64`, not `Float32`) before writing test instantiations:

```bash
grep -A 5 "fn __init__" shared/data/transforms.mojo | head -10
```

### Step 6: Commit and PR

```bash
git add shared/__init__.mojo shared/data/__init__.mojo tests/shared/integration/test_packaging.mojo
git commit -m "feat(data): re-export Normalize and Compose from shared.data and shared

Closes #<issue>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
git push -u origin <branch>
gh pr create --title "feat(data): re-export ..." --body "Closes #<issue>" --label "implementation"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `Float32` in test instantiation | `var normalizer = Normalize(Float32(0.5), Float32(0.5))` | `Normalize.__init__` takes `Float64`, not `Float32` — compile error | Always grep the leaf module's `__init__` signature before writing test code |
| Running `pixi run mojo package shared` locally | Tried to validate the build locally | GLIBC version too old on the dev host (requires 2.32+, host has older) | Mojo cannot run locally on this host; rely on CI for build validation |
| Checking `just --list` for build recipes | Ran `just --list` to find build targets | `just` not installed in PATH | Use `pixi run mojo` directly or rely on CI |

## Results & Parameters

### Minimal change set (3 files)

```text
shared/data/__init__.mojo          — add from shared.data.transforms import (Normalize, Compose)
shared/__init__.mojo               — add from shared.data import Normalize, Compose
tests/shared/integration/test_packaging.mojo — add 2 tests + register in main()
```

### Import path pattern after change

```mojo
# Full path (unchanged, still works)
from shared.data.transforms import Normalize, Compose

# New: package-level convenience
from shared.data import Normalize, Compose

# New: top-level convenience
from shared import Normalize, Compose
```

### PR label

Use `implementation` label. Auto-merge with `--rebase`.

### Pre-commit hooks that run

- `mojo format` — auto-formats `.mojo` files (no manual formatting needed)
- `trailing-whitespace`, `end-of-file-fixer` — cosmetic checks, always pass on new imports
- `check-added-large-files` — not applicable
