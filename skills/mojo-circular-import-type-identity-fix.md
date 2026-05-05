---
name: mojo-circular-import-type-identity-fix
description: "Fix Mojo 'cannot implicitly convert X to X' errors caused by circular imports that trigger dual type compilation. Use when: (1) Mojo compiler reports 'cannot implicitly convert Type to Type' where both types have the same name, (2) cross-package imports create A->B->A cycles in Mojo, (3) struct operators delegate to external modules that import the struct back, (4) typed dispatch files create reverse dependencies back to the public API package, (5) Tensor[dtype] and AnyTensor coexist in the same file causing overload ambiguity, (6) designing dual-type tensor APIs or reviewing parametric struct migrations."
category: architecture
date: 2026-03-23
version: "2.4.0"
user-invocable: false
tags:
  - mojo
  - circular-imports
  - type-identity
  - operators
  - architecture
  - tensor
  - overload-ambiguity
  - method-wrappers
absorbed:
  - mojo-dual-type-tensor-review (2026-03-21)
  - mojo-method-api-symmetry (2026-03-15)
  - mojo-method-wrapper-circular-import (2026-03-07)
  - mojo-overload-ambiguity-typed-tensor-isolation (2026-03-22)
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
| ProjectOdyssey | Issue #4998, PRs #5030-5058 | 242 build errors from typed ops, resolved by typed package isolation |
| ProjectOdyssey | PR #4803 | Thin method wrappers for split/tile/repeat/permute on ExTensor |
| ProjectOdyssey | PR #3803 | Local-scope import pattern for tile/repeat/permute/split method wrappers |

## Dual-Type Tensor Architecture Design

Absorbed from `mojo-dual-type-tensor-review` (2026-03-21, Epic #4998, Mojo 0.26.1).

### Architecture

```mojo
trait TensorLike(Copyable, Movable):
    fn numel(self) -> Int
    fn shape(self) -> List[Int]
    fn dtype(self) -> DType

struct Tensor[dtype: DType = DType.float32](TensorLike):
    var _data: UnsafePointer[Scalar[Self.dtype], origin=MutAnyOrigin]
    fn __getitem__(self, i: Int) raises -> Scalar[Self.dtype]: ...
    fn as_any(self) -> AnyTensor: ...
    fn cast[target: DType](self) raises -> Tensor[target]: ...

struct AnyTensor(TensorLike):
    var _data: UnsafePointer[UInt8, origin=MutAnyOrigin]
    var _dtype: DType
    fn as_tensor[dtype: DType](self) raises -> Tensor[dtype]: ...
    fn set(mut self, index: Int, value: Float64) raises: ...
```

Naming convention follows Mojo stdlib (`AnyType`, `AnyOrigin` → `AnyTensor`).

### Quantitative Codebase Audit

Before designing the dual-type system, count all affected sites:

| Metric | Count |
| ------- | ------- |
| Functions taking the tensor type | 368 |
| Functions returning the tensor type | 480 |
| Runtime dtype branch checks | 351 |
| Bitcast pointer accesses | 708 |

### Mojo 0.26.1 Parametric Capabilities

| Capability | Works? | Notes |
| ----------- | ------- | ------- |
| Parametric struct conforming to trait | YES | |
| `comptime Alias = OriginalType` for backward compat | YES | |
| Auto-parameterization for return types | NO (BLOCKER) | `fn relu(t: Tensor) -> Tensor` fails with "failed to infer parameter dtype" |
| `List[TraitName]` trait objects (existentials) | NO | Mojo 0.26.1 has no existential types |
| `Variant[TypeA, TypeB]` tagged union | YES | |
| Multi-param structs `Batch[data_dt, label_dt]` | YES | |
| Zero-copy bitcast views (ASAP destruction safe) | YES | |
| Default parameter values | YES | |
| Chained auto-param function calls | Partial | Requires explicit `[dt: DType]` |

Key constraint: always use explicit `[dt: DType]` on every function returning a parametric type.

```mojo
# FAILS: auto-param on return type
fn relu(t: Tensor) -> Tensor

# WORKS: explicit parameter
fn relu[dt: DType](t: Tensor[dt]) -> Tensor[dt]
# Call sites still infer dt: relu(my_tensor) works
```

### Review Findings Summary

```text
BLOCKERS (2):
  - Auto-param doesn't work for return types (must use explicit [dt: DType])
  - lazy_expression.mojo / lazy_eval.mojo missing from migration phases

HIGH (6):
  - Slice pointer arithmetic double-offset (remove * dtype_size for typed ptr)
  - I/O boundary underspecified (save via as_any(), load returns AnyTensor)
  - Phase 3->5 circular dependency (concatenate/stack/split use List[ExTensor])
  - __str__/__repr__ use _get_float64 (need typed access)
  - Scope underestimated 30-50% (explicit [dt: DType] on 480 signatures)
  - Binary bloat risk (eager instantiation, 317 fns x 11 dtypes)

MEDIUM (5):
  - In-place operator precision bug (pre-existing)
  - __hash__ precision loss for int types
  - Hashable not specified in TensorLike trait
  - SIMD helpers should merge to single parametric version
  - Circular import in tensor_io.mojo

Bugs found during audit (fixed in PR #5001):
  - conv2d: no dtype guard on kernel/bias vs input
  - batch_norm2d: no dtype guard on gamma/beta/running_stats vs input
  - attention: no dtype guard on mask vs scores
```

### Performance: Eager Instantiation

- Mojo uses eager instantiation (like C++ templates): N functions x M dtypes = N*M compiled bodies
- 317 functions x 11 dtypes = 3,487 worst-case instantiations
- Mitigation: restrict to 3 float types initially (float16/32/64)
- Memory pool is byte-level, dtype-agnostic — no impact

### Mojo 0.26.1 Documentation References

```text
Parameters:     github.com/modular/modular/blob/modular/v26.1/mojo/docs/manual/parameters/index.mdx
Traits:         github.com/modular/modular/blob/modular/v26.1/mojo/docs/manual/traits.mdx
Types (SIMD):   github.com/modular/modular/blob/modular/v26.1/mojo/docs/manual/types.mdx
UnsafePointer:  github.com/modular/modular/blob/modular/v26.1/mojo/docs/manual/pointers/unsafe-pointers.mdx
Lifecycle:      github.com/modular/modular/blob/modular/v26.1/mojo/docs/manual/lifecycle/life.mdx
```

### Failed Attempts (Dual-Type Design)

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Pure parametric ExTensor | Make ExTensor[dtype] the only type | Heterogeneous collections (List[ExTensor], Dict, Batch) break with no trait objects | Mojo 0.26.1 has no existential types; need a type-erased companion |
| Auto-parameterization for all functions | Rely on `fn relu(t: Tensor) -> Tensor` auto-inference | Return type auto-param fails: "failed to infer parameter dtype" | Must use explicit `[dt: DType]` on every function returning a parametric type |
| Change __getitem__ to return Float64 | Wider return type to accept more assignments | Float32 can't implicitly convert to Float64 in Mojo; broke 108 call sites | Mojo has zero implicit numeric conversions between float types |
| Proxy/reference return type from __getitem__ | Return a mutable proxy that accepts any assignment | "expression must be mutable in assignment" — Mojo ownership prevents mutable references from __getitem__ | Mojo's ownership model doesn't support reference-returning subscript |
| Single-pass sub-agent migration | Launch 8 agents to fix all files at once | Agents only fixed 60% of errors; missed Float16 paths, arithmetic mismatches, parallelize closures | Sub-agents need explicit error categories and line numbers; plan for 2-3 rounds |

## Typed Tensor Package Isolation (Overload Ambiguity Fix)

Absorbed from `mojo-overload-ambiguity-typed-tensor-isolation` (2026-03-22, Mojo 0.26.1).

### Root Cause

Mojo 0.26.1's overload resolver fails when a file has BOTH:
- Functions taking/returning `AnyTensor`
- Functions taking/returning `Tensor[dtype]` (or `Tensor` imported in scope)

The error `cannot implicitly convert 'AnyTensor' value to 'AnyTensor'` is misleading — it means the compiler found multiple candidate overloads and couldn't pick one. Having `Tensor` in scope creates phantom candidates that confuse resolution. Even PRIVATE functions with `Tensor[dtype]` signatures in the same file cause ambiguity.

Key evidence: 188 of 242 errors were this exact "AnyTensor to AnyTensor" message; error count was proportional to the number of `Tensor[dtype]` functions in scope.

### Fix: Extract Typed Code to Isolated Package

```bash
# BEFORE (broken): shared/core/arithmetic.mojo
from shared.tensor.tensor import Tensor  # THIS CAUSES THE PROBLEM
fn _add_typed[dt: DType](a: Tensor[dt], b: Tensor[dt]) -> Tensor[dt]: ...
fn add(a: AnyTensor, b: AnyTensor) -> AnyTensor: ...  # compiler confused

# AFTER (works): shared/core/arithmetic.mojo — NO Tensor import
fn add(a: AnyTensor, b: AnyTensor) -> AnyTensor:
    from shared.tensor.typed.arithmetic import _dispatch_add  # local import
    return _dispatch_add(a, b)

# shared/tensor/typed/arithmetic.mojo — isolated typed code
from shared.tensor.tensor import Tensor
fn _add_typed[dt: DType](a: Tensor[dt], b: Tensor[dt]) -> Tensor[dt]: ...
fn _dispatch_add(a: AnyTensor, b: AnyTensor) -> AnyTensor: ...
```

### Isolated Package Architecture

```text
shared/tensor/typed/          <- ISOLATED: typed implementations
  arithmetic.mojo               _broadcast_binary_typed[dtype, op]()
  elementwise.mojo              _unary_typed[dt, op]()
  activation.mojo               _relu_typed[dt](), _dispatch_relu()
  matrix.mojo                   _matmul_typed[dt]()
  reduction.mojo                _sum_typed[dt]()

shared/core/                  <- CLEAN: AnyTensor-only operations
  arithmetic.mojo               fn add(a: AnyTensor, b: AnyTensor)
  elementwise.mojo              fn exp(tensor: AnyTensor)
  activation.mojo               fn relu(tensor: AnyTensor)
  any_tensor.mojo               struct AnyTensor (keeps Tensor import for as_tensor)
  layers/linear.mojo            struct Linear[dtype] (keeps Tensor import)
```

### Files That Legitimately Keep Tensor Import

- `shared/tensor/tensor.mojo` — the struct itself
- `shared/tensor/factories.mojo` — factory functions
- `shared/core/any_tensor.mojo` — `as_tensor[dtype]()` method
- `shared/core/layers/linear.mojo` — `Linear[dtype]` parametric struct
- `shared/core/layers/conv2d.mojo` — `Conv2dLayer[dtype]` parametric struct
- `shared/core/layers/batchnorm.mojo` — `BatchNorm2dLayer[dtype]` parametric struct

### Mojo 0.26.1 Type Resolution Rules

```text
1. Importing Tensor[dtype] in a file pollutes overload resolution for ALL functions
2. Even private functions with Tensor[dtype] signatures cause ambiguity
3. .as_any() returning AnyTensor is seen as ambiguous when Tensor is in scope
4. Local-scope imports (inside function bodies) DO NOT pollute — they're deferred
5. The error message "cannot convert AnyTensor to AnyTensor" is MISLEADING —
   it means "multiple overload candidates found, can't pick one"
```

### Verification Commands

```bash
# No Tensor import in core operation files (should return NOTHING):
grep -l "from shared.tensor.tensor import Tensor" \
  shared/core/arithmetic.mojo shared/core/elementwise.mojo \
  shared/core/activation.mojo shared/core/matrix.mojo

# Typed files exist:
ls shared/tensor/typed/*.mojo

# Build passes:
just package
```

### Failed Attempts (Overload Ambiguity)

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Public typed wrappers (`add_typed`, `relu_typed`) | Added public `fn add_typed[dt: DType](a: Tensor[dt])` alongside `fn add(a: AnyTensor)` | 242 Mojo overload resolution errors — compiler couldn't disambiguate | Having `Tensor[dtype]` in scope AT ALL (even in private functions) pollutes overload resolution |
| Removing only public wrappers | Removed `add_typed` etc. but kept internal `_add_typed` and `_dispatch_add` in same file | Same 242 errors persisted | The issue is the `Tensor` TYPE being imported, not function visibility |
| Renaming typed functions | Different naming conventions to avoid collisions | Errors remained | Mojo's issue is with `Tensor[dtype]` type being in the same compilation scope |
| Fixing Self.dtype and removing exports | Fixed `dtype` → `Self.dtype`, removed typed exports from `__init__.mojo` | Reduced errors from 242 to ~200 but core ambiguity remained | Cosmetic fixes don't solve fundamental type scope pollution |

## Method Wrappers: Local-Scope Import Pattern

Absorbed from `mojo-method-wrapper-circular-import` (2026-03-07, PR #3803) and
`mojo-method-api-symmetry` (2026-03-15, PR #4803).

### Pattern Overview

When a struct (`ExTensor`) needs ergonomic method-style wrappers for operations that live in a
separate module that already imports the struct at module level, use **local-scope imports
inside each method body** to defer resolution to call time.

```text
extensor.mojo  --imports-->  (nothing from shape.mojo at module level)
shape.mojo     --imports-->  ExTensor from extensor.mojo

Adding top-level import would create:
extensor.mojo  --imports-->  shape.mojo  --imports-->  extensor.mojo  CIRCULAR
```

### Method Wrapper Template

```mojo
fn tile(self, reps: List[Int]) raises -> ExTensor:
    """Tile tensor by repeating along each dimension.

    Delegates to the functional `tile()` in `shared.core.shape`.

    Args:
        reps: Number of repetitions along each dimension.

    Returns:
        Tiled tensor with shape[i] = input_shape[i] * reps[i].
    """
    from shared.core.shape import tile as _tile   # local-scope import
    return _tile(self, reps)
```

Key details:
- Import is **inside the method body** — never at module level
- Use `as _alias` to avoid shadowing the method name itself
- For `List`-returning methods, use `^` transfer operator for ownership:

```mojo
fn split(self, num_splits: Int, axis: Int = 0) raises -> List[ExTensor]:
    from shared.core.shape import split as _split
    return _split(self, num_splits, axis)^   # ^ transfers ownership
```

### Copy-Paste Method Templates (tile/repeat/permute/split)

```mojo
fn tile(self, reps: List[Int]) raises -> ExTensor:
    from shared.core.shape import tile as _tile
    return _tile(self, reps)

fn repeat(self, n: Int, axis: Int = -1) raises -> ExTensor:
    from shared.core.shape import repeat as _repeat
    return _repeat(self, n, axis)

fn permute(self, dims: List[Int]) raises -> ExTensor:
    from shared.core.shape import permute as _permute
    return _permute(self, dims)

fn split(self, num_splits: Int, axis: Int = 0) raises -> List[ExTensor]:
    from shared.core.shape import split as _split
    return _split(self, num_splits, axis)^
```

### Placement Rule

Insert wrappers **after** the last existing method they logically extend. For
`tile/repeat/permute/split`, place after `slice()` — the analogous existing method wrapper
for a shape operation.

### API Symmetry Audit Workflow

When closing "API symmetry" or "method wrapper" issues:

```bash
# 1. Find what's exported from the module
grep -n "split\|tile\|repeat" shared/core/__init__.mojo

# 2. Find what methods already exist on the struct
grep -n "^    fn " shared/core/extensor.mojo | grep -E "split|tile|repeat"

# 3. Find the last method in the struct (insertion point)
grep -n "^    fn \|^fn \|^struct " shared/core/extensor.mojo | tail -20
```

The difference between (1) and (2) is the set of missing wrappers.

### Test Pattern: Symmetry Verification

Keep test files to ≤10 `fn test_` functions per file.

```mojo
fn test_split_with_indices_method_vs_free_fn() raises:
    """Verify method output matches free function (symmetry test)."""
    var a = arange(0.0, 10.0, 1.0, DType.float32)
    var indices = List[Int]()
    indices.append(3)
    indices.append(7)

    var method_parts = a.split_with_indices(indices)
    var free_parts = split_with_indices(a, indices)

    if len(method_parts) != len(free_parts):
        raise Error("Method and free function should return same number of parts")

    for i in range(len(method_parts)):
        if method_parts[i].numel() != free_parts[i].numel():
            raise Error("Part sizes should match between method and free function")
```

### Gotcha: assert_value_at message= keyword

The `assert_value_at` signature is `(tensor, index, expected, tolerance, message)`.
Passing a string as the 4th positional argument fails because Mojo tries to convert it to
`Float64`. Always use the `message=` keyword:

```mojo
# WRONG — string interpreted as tolerance: Float64
assert_value_at(parts[0], 0, 0.0, "should be 0.0")

# CORRECT — message= keyword bypasses the tolerance parameter
assert_value_at(parts[0], 0, 0.0, message="should be 0.0")
```

### Running Tests in a Worktree

```bash
# Use explicit PIXI_PROJECT_MANIFEST when in a worktree
PIXI_PROJECT_MANIFEST=/path/to/worktree/pixi.toml pixi run mojo tests/shared/core/test_extensor_method_api.mojo

# Commit with SKIP=mojo-format if on incompatible GLIBC host
SKIP=mojo-format git commit -m "feat(extensor): add split_with_indices method wrapper"
```

Note: Mojo v0.26.1 has no `mojo test` subcommand — use `pixi run mojo <file>` directly.

### Failed Attempts (Method Wrappers)

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Top-level import | Added `from shared.core.shape import tile, repeat, permute, split` at top of `extensor.mojo` | Creates circular import: `extensor → shape → extensor` | Mojo resolves module-level imports eagerly; circular deps at module level are fatal |
| Re-implementing logic | Copying implementation from `shape.mojo` into each method | Violates DRY; doubles maintenance burden | Never duplicate logic; use delegation |
| `alias` trick | Tried using `alias` to defer the import | Alias is compile-time constant, not a deferred import mechanism | Only function-body imports in Mojo can avoid circular resolution |
| Passing message as 4th positional arg to `assert_value_at` | Called `assert_value_at(tensor, idx, 0.0, "message")` | Mojo tried to convert `StringLiteral` to `Float64` for tolerance parameter | Always use `message=` keyword argument; check function signature before writing tests |
| Running `pixi run mojo test` | Used `mojo test` subcommand | Mojo v0.26.1 has no `test` subcommand; only `mojo <file>` works | Use `pixi run mojo <file>` directly to run test files |
