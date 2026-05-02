---
name: mojo-circular-import-type-identity-fix
description: "Fix Mojo 'cannot implicitly convert X to X' errors caused by circular imports that trigger dual type compilation. Use when: (1) Mojo compiler reports 'cannot implicitly convert Type to Type' where both types have the same name, (2) cross-package imports create A->B->A cycles in Mojo, (3) struct operators delegate to external modules that import the struct back, (4) typed dispatch files create reverse dependencies back to the public API package."
category: architecture
date: 2026-03-23
version: "2.0.0"
user-invocable: false
tags:
  - mojo
  - circular-imports
  - type-identity
  - operators
  - architecture
---

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-23 |
| **Objective** | Fix 255+ CI compilation errors ("cannot implicitly convert 'AnyTensor' to 'AnyTensor'") caused by circular imports between shared.core and shared.tensor packages |
| **Outcome** | Successful in two phases: Phase 1 (PR #5062) moved AnyTensor, Phase 2 (PR #5063) broke remaining circular deps by deleting fake wrappers and extracting utilities |

## When to Use

- Mojo compiler reports `cannot implicitly convert 'X' value to 'X'` where both sides are the SAME type name
- Two Mojo modules import each other (directly or transitively), even via function-scoped imports
- A struct's operator methods (`__add__`, etc.) delegate to external module functions that import the struct type
- A Mojo package `__init__.mojo` re-exports types from another package that imports back
- Build worked before a refactoring that split types across packages
- "Typed dispatch" files import back into the public API package they're supposed to serve

## Verified Workflow

### Quick Reference

```text
Root cause diagnosis:
  1. Grep for the type name in error: "cannot implicitly convert 'X' to 'X'"
  2. Find ALL files that define struct X (should be exactly 1)
  3. Trace the import chain: X.mojo -> Y.mojo -> ... -> X.mojo (cycle!)
  4. The cycle causes Mojo to compile X.mojo twice with different type identities

Fix strategy (in priority order):
  A. Delete fake wrappers: If a "typed" file just roundtrips through AnyTensor with zero callers, delete it
  B. Extract utilities: Move pure utility functions (no tensor deps) to a base package
  C. Function-scoped imports: Convert module-level imports to function-body imports (deferred resolution)
  D. Co-locate: Move files into the same package (siblings can import each other)
  E. Inline operators: Implement math on the struct using internal data, not external functions
  F. Remove re-exports: Don't re-export types in __init__.mojo across package boundaries
```

### Detailed Steps

#### Step 1: Identify the circular import chain

```bash
# Find where the type is defined
grep -rn "struct AnyTensor" --include="*.mojo" .

# Find all cross-package imports that create cycles
# Package A -> Package B:
grep -rn "^from shared\.tensor\.typed" shared/core/ --include="*.mojo"
# Package B -> Package A (REVERSE — this is the problem):
grep -rn "^from shared\.core" shared/tensor/typed/ --include="*.mojo"
```

#### Step 2: Classify each reverse import

| Classification | Action | Example |
| ---------------- | -------- | --------- |
| **Fake typed wrapper** (converts Tensor→AnyTensor, calls core fn, converts back) with zero callers | **DELETE** | `typed/matrix.mojo`, `typed/reduction.mojo`, `typed/conv.mojo` |
| **Pure utility function** with no tensor dependencies | **MOVE** to `shared/base/` | `_resolve_shape` (just resolves -1 dims in shape lists) |
| **Function needed** but only in 1-2 call sites | **Function-scoped import** | `as_contiguous` in `typed/arithmetic.mojo` |
| **Constants-only import** | **KEEP** (no cycle risk) | `activation_constants` in `typed/activation.mojo` |

#### Step 3: Delete fake typed wrappers

A "fake typed wrapper" is a function that:
1. Takes `Tensor[dt]` or `AnyTensor` input
2. Converts to `AnyTensor` via `.as_any()`
3. Calls the `shared.core` function (e.g., `matmul`, `sum`)
4. Converts result back via `.as_tensor[dt]()`
5. Has **zero external callers**

```bash
# Verify zero callers before deleting
grep -rn "_dispatch_matmul_typed\|_dispatch_sum_typed\|_dispatch_conv2d_typed" \
  shared/ tests/ --include="*.mojo"
# If no matches → safe to delete

rm shared/tensor/typed/matrix.mojo
rm shared/tensor/typed/reduction.mojo
rm shared/tensor/typed/conv.mojo
```

#### Step 4: Extract pure utilities to base package

For functions with no tensor dependencies (only uses `List[Int]`, `String`, etc.):

```mojo
# Create shared/base/shape_utils.mojo
"""Shape utility functions with no tensor dependencies."""
from collections import List

fn _resolve_shape(new_shape: List[Int], total_elements: Int) raises -> List[Int]:
    # ... pure logic, no tensor imports needed
```

Update importers:
```mojo
# In shared/core/shape.mojo:
from shared.base.shape_utils import _resolve_shape

# In shared/tensor/typed/shape.mojo:
from shared.base.shape_utils import _resolve_shape
```

#### Step 5: Convert to function-scoped imports

For imports that can't be deleted or moved:

```mojo
# BEFORE (module-level — creates cycle):
from shared.core.shape import as_contiguous

fn _broadcast_binary_typed[...](a, b) raises -> ...:
    var a_cont = ... if a.is_contiguous() else as_contiguous(...)

# AFTER (function-scoped — defers resolution):
fn _broadcast_binary_typed[...](a, b) raises -> ...:
    # NOTE: Function-scoped import to avoid circular dependency
    from shared.core.shape import as_contiguous
    var a_cont = ... if a.is_contiguous() else as_contiguous(...)
```

#### Step 6: Verify the dependency graph

```bash
# No module-level function imports from core in tensor/typed:
grep -rn "^from shared\.core" shared/tensor/typed/ --include="*.mojo"
# Should only show constants imports (e.g., activation_constants)

# Function-scoped imports are indented (OK):
grep -rn "    from shared\.core" shared/tensor/typed/ --include="*.mojo"

# Build and test
mojo package -I "$REPO_ROOT" shared -o /tmp/shared.mojopkg
```

Target: `shared.base ← shared.tensor ← shared.core` (clean DAG, no cycles)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Moving AnyTensor only (Phase 1) | Moved AnyTensor from shared.core to shared.tensor | Fixed some cycles but shared.tensor.typed still imported from shared.core (matrix, reduction, conv, shape, arithmetic), maintaining the cycle | Moving a type to break one cycle can leave other cycles intact; must audit ALL cross-package imports |
| Checking import paths | Verified all files use `from shared.tensor.any_tensor import AnyTensor` (same path everywhere) | All paths were identical — the error persisted | Type identity errors are NOT caused by different import paths; they're caused by dual compilation contexts from circular deps |
| Function-scoped imports everywhere | Considered making ALL reverse imports function-scoped | Works as a band-aid for 1-2 imports but doesn't address fake wrapper files that shouldn't exist | Prefer deleting dead code over working around it; function-scoped imports are for imports that genuinely need to exist |
| Keep operators delegating to shared.core.arithmetic | Operators used `from shared.core.arithmetic import add` inside method bodies | shared.core.arithmetic imports AnyTensor at top level, creating shared.tensor.any_tensor -> shared.core.arithmetic -> shared.tensor.any_tensor cycle | Struct operators MUST be self-contained or delegate only to same-package functions |
| Create typed wrapper files that call back into shared.core | typed/matrix.mojo called shared.core.matrix.matmul (AnyTensor roundtrip) | Created reverse dependency AND added no real typed computation | Typed dispatch files must implement actual typed logic, not just wrap AnyTensor calls |

## Results & Parameters

### Dependency DAG (no cycles)

```text
shared/base/          (zero dependencies on other shared packages)
  |- shape_utils.mojo     (_resolve_shape — pure utility)
  |- broadcasting.mojo
  |- dtype_ordinal.mojo
  |
  v
shared/tensor/        (depends only on shared.base)
  |- tensor.mojo          (Tensor[dtype])
  |- any_tensor.mojo      (AnyTensor)
  |- typed/               (typed dispatch cores)
  |   |- activation.mojo    (real typed impl, imports only constants from core)
  |   |- elementwise.mojo   (real typed impl, no core imports)
  |   |- arithmetic.mojo    (function-scoped core import for as_contiguous)
  |   |- shape.mojo          (imports _resolve_shape from shared.base)
  |
  v
shared/core/          (depends on shared.tensor and shared.base)
  |- activation.mojo      (public API, dispatches to shared.tensor.typed)
  |- arithmetic.mojo      (public API, dispatches to shared.tensor.typed)
  |- shape.mojo            (public API, dispatches to shared.tensor.typed)
```

### Key Mojo Compiler Behavior

- **Type identity is per-compilation-unit**: If module A is compiled twice (via two different import paths), the types it defines are DIFFERENT types
- **Package `__init__.mojo` imports all submodules**: When any file in a package is imported, Mojo may compile the entire package including `__init__.mojo`
- **Function-scoped imports still trigger module compilation**: `from X import Y` inside a function body still causes X to be compiled, just deferred to call time
- **Constants-only imports are safe**: Importing compile-time constants doesn't create type identity issues
- **Cross-package re-exports are dangerous**: `shared/core/__init__.mojo` importing from `shared.tensor.any_tensor` means ANY import from `shared.core` can trigger `shared.tensor` compilation

### Decision Tree for Reverse Dependencies

```text
Found module-level import from Package A in Package B (reverse dep):

1. Is the file a pure wrapper with zero callers?
   YES → DELETE the file (safest, removes 100+ lines of dead code)

2. Is the imported function a pure utility with no package deps?
   YES → MOVE to shared/base/ (break the cycle at the root)

3. Is the import used in only 1-2 function bodies?
   YES → Convert to function-scoped import (deferred resolution)

4. Is it a constants-only import?
   YES → KEEP (constants don't create compilation cycles)

5. None of the above?
   → Consider co-locating or inlining the logic
```

### Impact (Combined Phases)

| Metric | Phase 1 (PR #5062) | Phase 2 (PR #5063) |
| -------- | -------------------- | -------------------- |
| Files changed | 590 | 8 |
| Lines added | ~2000 | 80 |
| Lines removed | ~2000 | 712 |
| Net lines | ~0 | -632 |
| Compilation errors fixed | 255+ initial | Remaining after Phase 1 |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PR #5062 | Phase 1: Moved AnyTensor from shared/core/ to shared/tensor/, inlined operators |
| ProjectOdyssey | PR #5063 | Phase 2: Deleted 3 fake typed wrappers, extracted _resolve_shape to shared/base, function-scoped imports |
