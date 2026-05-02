---
name: tensor-dtype-native-ops-inversion
description: "Invert wrapper pattern for parametric tensor operations: Tensor[dtype] typed cores with AnyTensor ordinal dispatch. Use when: migrating runtime-typed tensor ops to compile-time typed, eliminating dtype branching, designing 3-layer typed architecture."
category: architecture
date: 2026-03-22
version: "1.0.0"
user-invocable: false
tags: [mojo, tensor, dtype, parametric, refactor, typed-ops, dispatch, architecture]
---

# Tensor[dtype] Native Ops Inversion Pattern

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-22 |
| **Objective** | Invert wrapper pattern so Tensor[dtype] typed implementations are the core, AnyTensor dispatches to them |
| **Outcome** | 8 PRs merged: shared/base/ extraction, arithmetic/elementwise/activation/matrix/reduction/shape/comparison typed cores, AnyTensor delegation, 51 new tests |
| **Mojo Version** | 0.26.1 |
| **Scope** | ~6,500 lines across 20+ files |
| **Context** | ProjectOdyssey issue #4998, ADR-012 |

## When to Use

- Migrating from runtime-typed (`var _dtype: DType`) to compile-time typed (`struct T[dtype: DType]`) tensor operations
- Eliminating runtime dtype branching (if/elif cascades) and `_data.bitcast[T]()` calls from hot paths
- Designing a 3-layer architecture: public API -> dtype dispatch -> typed core
- Adding `Tensor[dtype]` overloads to existing AnyTensor operations
- Making AnyTensor operators delegate to typed implementations to reduce code duplication
- Breaking circular package dependencies between typed and runtime tensor packages

## Verified Workflow

### Quick Reference

```text
Architecture:
  Layer 1 (outer): AnyTensor public API  - fn add(a: AnyTensor, b: AnyTensor) -> AnyTensor
  Layer 2 (dispatch): ordinal-based      - dtype_to_ordinal() -> jump table
  Layer 3 (core): Tensor[dtype] typed    - fn _add_typed[dt](a: Tensor[dt], b: Tensor[dt]) -> Tensor[dt]

Key patterns:
  - Typed core uses _data pointer directly (zero bitcasts)
  - AnyTensor dispatch: a.as_tensor[dt]() -> typed_op -> result.as_any()
  - Local-scope imports for circular dependency avoidance
  - Existing parametric kernels (_conv2d_kernel[dtype], _matmul_impl[dtype]) wire directly to typed cores
```

### Step 1: Break Circular Dependencies First

Before inverting operations, extract modules with zero tensor dependencies to a base package:

```bash
# Identify candidates (zero tensor imports):
grep -L "ExTensor\|AnyTensor\|Tensor" shared/core/*.mojo

# Move with git mv:
mkdir -p shared/base
git mv shared/core/memory_pool.mojo shared/base/
git mv shared/core/broadcasting.mojo shared/base/
git mv shared/core/dtype_ordinal.mojo shared/base/

# Create shared/base/__init__.mojo with re-exports
# Add backward-compat re-exports in shared/core/__init__.mojo
```

Result: `shared/base/` <- `shared/tensor/` <- `shared/core/` (clean DAG).

### Step 2: Implement Typed Core (Layer 3)

For binary operations (add, subtract, multiply, divide):

```mojo
fn _add_typed[dt: DType](a: Tensor[dt], b: Tensor[dt]) raises -> Tensor[dt]:
    """Native typed addition with broadcasting. Zero dtype branches."""
    var a_cont = a if a.is_contiguous() else a.as_contiguous()
    var b_cont = b if b.is_contiguous() else b.as_contiguous()
    var result_shape = broadcast_shapes(a_cont.shape(), b_cont.shape())
    var result = Tensor[dt](result_shape)
    # ... broadcasting index logic (same as existing) ...
    for i in range(total_elems):
        result._data[result_idx] = a_cont._data[idx_a] + b_cont._data[idx_b]
    return result^
```

For unary operations (exp, log, sqrt, relu):

```mojo
fn _exp_typed[dt: DType](input: Tensor[dt]) raises -> Tensor[dt]:
    var result = Tensor[dt](input.shape())
    for i in range(input.numel()):
        result._data[i] = exp(input._data[i])
    return result^
```

### Step 3: Add Ordinal Dispatch (Layer 2)

```mojo
fn add(a: AnyTensor, b: AnyTensor) raises -> AnyTensor:
    if a._dtype != b._dtype:
        raise Error("Cannot add tensors with different dtypes")
    var ordinal = dtype_to_ordinal(a._dtype)
    if ordinal == DTYPE_FLOAT32:
        return _add_typed[DType.float32](
            a.as_tensor[DType.float32](), b.as_tensor[DType.float32]()
        ).as_any()
    elif ordinal == DTYPE_FLOAT64:
        return _add_typed[DType.float64](
            a.as_tensor[DType.float64](), b.as_tensor[DType.float64]()
        ).as_any()
    elif ordinal == DTYPE_FLOAT16:
        return _add_typed[DType.float16](
            a.as_tensor[DType.float16](), b.as_tensor[DType.float16]()
        ).as_any()
    # ... remaining dtypes (int8, int16, int32, int64, uint8-64)
    else:
        raise Error("Unsupported dtype for add")
```

### Step 4: Public Typed API (Layer 1)

```mojo
fn add[dt: DType](a: Tensor[dt], b: Tensor[dt]) raises -> Tensor[dt]:
    """Element-wise addition (typed version). Direct call, no dispatch."""
    return _add_typed[dt](a, b)
```

### Step 5: Make AnyTensor Operators Delegate

Use local-scope imports to avoid circular dependencies:

```mojo
# In any_tensor.mojo:
fn __iadd__(mut self, other: Self) raises:
    from shared.core.arithmetic import add  # Local import — no circular dep
    self = add(self, other)

fn __neg__(self) raises -> Self:
    from shared.core.elementwise import negate  # Local import
    return negate(self)
```

### Step 6: Wire Existing Parametric Kernels

Files with existing `[dtype: DType]` parametric kernels just need input/output type changes:

```mojo
# conv.mojo already has _conv2d_kernel[dtype]() — just wire it:
fn _conv2d_typed[dt: DType](input: Tensor[dt], kernel: Tensor[dt], ...) raises -> Tensor[dt]:
    # Delegates to existing _conv2d_kernel[dt] with Tensor._data pointers
    ...
```

### Step 7: Comprehensive Testing

Test equivalence between typed and AnyTensor paths:

```mojo
fn test_add_typed_matches_anytensor() raises:
    var a_any = ones([3, 4], DType.float32)
    var b_any = ones([3, 4], DType.float32)
    var result_any = add(a_any, b_any)

    var a_typed = typed_ones[DType.float32]([3, 4])
    var b_typed = typed_ones[DType.float32]([3, 4])
    var result_typed = add[DType.float32](a_typed, b_typed)

    for i in range(result_any.numel()):
        assert_almost_equal(Float64(result_any[i]), Float64(result_typed[i]), atol=1e-7)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Top-level import of arithmetic in any_tensor.mojo | `from shared.core.arithmetic import add` at module level | Circular import: any_tensor.mojo <- arithmetic.mojo <- any_tensor.mojo | Use local-scope imports inside method bodies (deferred to call time) |
| Auto-parameterization for return types | `fn relu(t: Tensor) -> Tensor` (no explicit `[dt: DType]`) | Mojo error: "failed to infer parameter 'dtype'" for return types | All functions returning Tensor must use explicit `[dt: DType]` parameter |
| Single-PR approach for all operations | Bundle all typed ops + AnyTensor delegation in one PR | Too many merge conflicts when parallel agents work on overlapping files | Split by operation category (arithmetic, elementwise, matrix, etc.) with separate PRs |
| Rebasing without conflict resolution strategy | Rebasing PR branches that modified same __init__.mojo exports | Import list conflicts in shared/core/__init__.mojo between concurrent PRs | Rebase sequentially and resolve export list conflicts by keeping all additions |
| Modifying AnyTensor god file (4,769 lines) concurrently | Multiple PRs touching any_tensor.mojo simultaneously | Merge conflicts in the same file from different angles | Sequence: typed ops in separate files first (PRs 2-5), then AnyTensor delegation last (PR 6) |
| Using `List[Module]` for heterogeneous layer containers | Tried to create `List[Module]` for sequential models | Mojo has no trait objects / heap dispatch — `List[Trait]` doesn't compile | Use parametric `Sequential2[T0: Module, T1: Module]` resolved at compile time |

## Results & Parameters

### PR Sequence (8 PRs, ~6,450 lines)

```yaml
pr_sequence:
  - name: "shared/base/ extraction"
    scope: "~250 lines"
    risk: "low"
    description: "Move 6 zero-dependency files to break circular import"

  - name: "Arithmetic typed ops"
    scope: "~1,000 lines"
    risk: "medium"
    description: "Invert add/sub/mul/div/mod/pow to typed-first"

  - name: "Elementwise + activation typed ops"
    scope: "~1,500 lines"
    risk: "medium"
    description: "exp/log/sqrt/sin/cos/relu/sigmoid/tanh to typed-first"
    note: "Can parallelize with arithmetic PR"

  - name: "Matrix + reduction typed ops"
    scope: "~1,300 lines"
    risk: "medium"
    description: "matmul/transpose/dot/sum/mean/conv2d to typed-first"
    note: "Can parallelize with arithmetic PR"

  - name: "Shape + comparison + remaining"
    scope: "~1,200 lines"
    risk: "medium"
    description: "reshape/flatten/equal/less/batch_norm/loss/strassen"

  - name: "AnyTensor delegation"
    scope: "~500 lines"
    risk: "high"
    description: "Operators delegate to typed implementations"
    constraint: "Must run AFTER all typed ops PRs are merged"

  - name: "Audit minor fixes"
    scope: "~100 lines"
    risk: "low"
    description: "Stale comments, exports, documentation"

  - name: "Tests"
    scope: "~600 lines (51 test functions)"
    risk: "low"
    description: "Equivalence, precision, dispatch, import tests"
```

### Key Configuration

```yaml
mojo_version: "0.26.1"
build_command: "just package"
test_command: "just test-mojo"
format_command: "just pre-commit-all"
container: "just podman-up && just shell"
dispatch_pattern: "ordinal-based (dtype_to_ordinal -> if/elif cascade)"
supported_dtypes: [float16, float32, float64, int8, int16, int32, int64, uint8, uint16, uint32, uint64]
circular_import_fix: "local-scope imports inside method bodies"
bfloat16_cast: "BFloat16(Float32(value)) / Float64(Float32(ptr[]))"
```

### Architecture Diagram

```text
shared/base/                    ← Layer 0: Zero tensor dependencies
  memory_pool.mojo                 (stdlib only)
  broadcasting.mojo
  dtype_ordinal.mojo
  defaults.mojo, constants...

shared/tensor/                  ← Layer 1: Compile-time typed tensor
  tensor.mojo                     struct Tensor[dtype: DType]
  tensor_traits.mojo              trait TensorLike
  factories.mojo                  zeros[dtype], ones[dtype], ...

shared/core/                    ← Layer 2: Operations + runtime tensor
  any_tensor.mojo                 struct AnyTensor (runtime-typed)
  arithmetic.mojo                 add[dt]() typed core + AnyTensor dispatch
  elementwise.mojo                exp[dt](), log[dt](), ...
  activation.mojo                 relu[dt](), sigmoid[dt](), ...
  matrix.mojo                     matmul[dt](), transpose[dt](), ...
  reduction.mojo                  sum[dt](), mean[dt](), ...
  ...
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #4998, PRs #5030-5035 + #5049-5050 | 8 PRs, ~6,450 lines, ADR-012 implementation |
