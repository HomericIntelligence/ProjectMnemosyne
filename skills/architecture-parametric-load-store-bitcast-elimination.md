---
name: architecture-parametric-load-store-bitcast-elimination
description: "Add parametric load[dtype]/store[dtype]/data_ptr[dtype] API to AnyTensor to eliminate raw _data.bitcast UAF vulnerabilities. Use when: (1) raw _data.bitcast[T]() patterns cause ASAP destruction UAF in Mojo, (2) designing safe element access for runtime-typed tensors, (3) migrating bulk pointer patterns to a centralized API, (4) uniform test weights cause numerical overflow through deep networks."
category: architecture
date: 2026-03-27
version: "1.1.0"
user-invocable: false
history: architecture-parametric-load-store-bitcast-elimination.history
tags:
  - mojo
  - tensor
  - bitcast
  - uaf
  - asan
  - load-store
  - parametric
  - api-design
  - numerical-stability
---

# Parametric load[dtype]/store[dtype] API for Bitcast UAF Elimination

Design and implement a parametric element access API that replaces raw `_data.bitcast[T]()`
patterns to prevent ASAP destruction use-after-free in Mojo.

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Eliminate 101+ raw bitcast patterns in shared/training/ that cause UAF crashes in CI |
| **Outcome** | Success -- zero `_data.bitcast` patterns remain in shared/training/, all ASAN tests pass |
| **Repository** | ProjectOdyssey |
| **PR** | #5097 |

## When to Use

- Mojo code crashes with `libKGENCompilerRTShared.so` after extracting pointers via `_data.bitcast[T]()`
- ASAN reports `heap-use-after-free` where `Tensor.__del__` freed memory before bitcast pointer dereference
- Designing safe element access for a runtime-typed tensor struct (dtype stored as field, not type parameter)
- Need per-element typed access without runtime dtype dispatch overhead
- Migrating SIMD bulk pointer patterns to a centralized, auditable API
- Uniform test weights (`full(shape, scale)`) cause `inf` overflow through deep conv networks
- Pooling operations crash with NaN/Inf on float16 tensors (bitcast[Float32] reads wrong offsets)
- Any `_data.bitcast[Float32]()` in code that handles multiple dtypes (float16, float32, float64)

## Verified Workflow

### Quick Reference

```mojo
# Per-element access (safe from ASAP destruction UAF):
var val = tensor.load[DType.float32](index)      # Read
tensor.store[DType.float32](index, Float32(val))  # Write

# Bulk pointer (for SIMD/tight loops -- caller must keep tensor alive):
var ptr = tensor.data_ptr[DType.float32]()
for i in range(tensor.numel()):
    ptr[i] = ...

# ASAN verification:
# pixi run mojo build --sanitize address -g -I "$(pwd)" -I . -o /tmp/test <file>
# /tmp/test
```

### Detailed Steps

#### Step 1: Add the API to AnyTensor

Insert after the existing `_set_int32` method (around line 1622):

```mojo
@always_inline
fn load[dtype: DType](self, index: Int) -> Scalar[dtype]:
    debug_assert(self._dtype == dtype, "AnyTensor.load[dtype] mismatch")
    return self._data.bitcast[Scalar[dtype]]()[index]

@always_inline
fn store[dtype: DType](self, index: Int, value: Scalar[dtype]):
    debug_assert(self._dtype == dtype, "AnyTensor.store[dtype] mismatch")
    self._data.bitcast[Scalar[dtype]]()[index] = value

@always_inline
fn data_ptr[dtype: DType](self) -> UnsafePointer[Scalar[dtype], origin=MutAnyOrigin]:
    debug_assert(self._dtype == dtype, "AnyTensor.data_ptr[dtype] mismatch")
    return self._data.bitcast[Scalar[dtype]]()
```

**Key design decisions:**
- `self` not `mut self` -- existing `_set_float32` uses `self` because `_data` has `origin=MutAnyOrigin`
- `@always_inline` -- zero overhead vs raw bitcast
- `debug_assert` -- catches dtype mismatches in debug, compiles away in release
- No bounds check -- matches existing `_get_float32` for inner loop performance
- Parametric method on non-parametric struct works in Mojo 0.26.1 (proven by `as_tensor[dtype]`)
- Named `load`/`store` not `get`/`set` to avoid conflict with existing 12 `set()` overloads

#### Step 2: Migrate per-element patterns

```mojo
# BEFORE (UAF risk -- tensor may be ASAP-destroyed):
var loss_value = Float64(loss_tensor._data.bitcast[Float32]()[0])

# AFTER (safe -- self alive for duration of call):
var loss_value = Float64(loss_tensor.load[DType.float32](0))
```

#### Step 3: Migrate bulk pointer loops

```mojo
# BEFORE (UAF risk in tight loops):
var param_data = param._data.bitcast[Float32]()
var grad_data = grad._data.bitcast[Float32]()
for i in range(numel):
    param_data[i] += grad_data[i]

# AFTER (safe per-element access):
for i in range(numel):
    param.store[DType.float32](i, param.load[DType.float32](i) + grad.load[DType.float32](i))

# OR for SIMD patterns (data_ptr still needs tensor alive):
var param_ptr = param.data_ptr[DType.float32]()
var grad_ptr = grad.data_ptr[DType.float32]()
for i in range(numel):
    param_ptr[i] += grad_ptr[i]
```

#### Step 4: Fix uniform weight numerical overflow

```mojo
# BEFORE (He init with uniform weights -- exponential growth):
var scale = sqrt(2.0 / Float64(fan_in))  # Per-layer gain = sqrt(2*fan_in) >> 1.0

# AFTER (uniform scaling -- per-layer gain = 1.0):
var scale = 1.0 / Float64(fan_in)
```

He init (`sqrt(2/fan_in)`) assumes random weights where positive/negative cancel.
With `full(shape, scale)` (all-same values), every value adds constructively,
giving gain = `fan_in * scale = sqrt(2 * fan_in)` per layer. Through 13 VGG16
conv layers, this grows to `inf`.

#### Step 5: Verify with ASAN

```bash
pixi run mojo build --sanitize address -g -I "$(pwd)" -I . \
    -o /tmp/test_asan tests/shared/training/test_training_loop.mojo
/tmp/test_asan
# Expected: All tests pass, zero UAF/bad-free errors
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Named `get[dtype]`/`set[dtype]` | Used get/set as method names | Conflicts with existing 12 `set()` overloads on AnyTensor | Use `load`/`store` (LLVM/SIMD terminology) to avoid name conflicts |
| Both agents adding API independently | Parallel sub-agents both added load/store/data_ptr to any_tensor.mojo | Cherry-pick created duplicate blocks with conflicting signatures (one missing `origin=MutAnyOrigin`) | When agents modify the same file, one should add the API and the other should only use it |
| `data_ptr` without `origin=MutAnyOrigin` | Agent's version returned `UnsafePointer[Scalar[dtype]]` | Compile error -- return type doesn't match `_data.bitcast` which has `origin=MutAnyOrigin` | Always include `origin=MutAnyOrigin` on returned pointers from AnyTensor |
| `sizeof[Scalar[dtype]]()` for offset | Tried to compute byte offset manually | Not available in Mojo 0.26.1 stdlib | Use `self._data.bitcast[Scalar[dtype]]()[index]` -- pointer arithmetic handles sizing automatically |
| He init with uniform weights in VGG16 test | `full(shape, sqrt(2/fan_in))` for all-same weights | Exponential growth: gain per layer = `sqrt(2*fan_in)`, not 1.0 like random He init | He init assumes random (cancellation); uniform weights need `1/fan_in` for unit gain |
| Pooling bitcast[Float32] on float16 tensors | `x._data.bitcast[Float32]()[in_idx]` in all 6 pooling functions | Float16 = 2 bytes but bitcast[Float32] reads 4 bytes at `base + idx*4` — wrong offsets, garbage NaN/Inf | Use `_get_float64(idx)` / `_set_float64(idx, val)` which handles all dtypes correctly via proper byte sizing |
| Missed pooling module in initial migration | Migrated shared/training/ (101 patterns) but left shared/core/pooling.mojo | Pooling has 6 functions with bitcast reads/writes; float16 tests crash with "max pooling output contains NaN or Inf" | After any bitcast migration, grep the ENTIRE codebase for remaining patterns — `grep -rn "bitcast\[Float32\]" shared/` |

## Results & Parameters

### API Design

```yaml
# Three methods added to AnyTensor:
load[dtype: DType](self, index: Int) -> Scalar[dtype]     # Per-element read
store[dtype: DType](self, index: Int, value: Scalar[dtype]) # Per-element write
data_ptr[dtype: DType](self) -> UnsafePointer[Scalar[dtype]] # Bulk pointer

# Properties:
inline: "@always_inline"
bounds_check: "none (caller responsible)"
dtype_check: "debug_assert only (compiles away in release)"
self_mutability: "self (not mut self) -- MutAnyOrigin allows writes"
```

### Migration Statistics

```yaml
training_module:
  files_modified: 12
  bitcast_patterns_replaced: 101+
  remaining_raw_bitcasts: 0
  asan_errors_before: "bad-free + heap-use-after-free"
  asan_errors_after: 0

pooling_module:
  file: "shared/core/pooling.mojo"
  functions_fixed: 6  # maxpool2d, avgpool2d, global_avgpool2d (fwd + bwd each)
  pattern: "_data.bitcast[Float32]()[idx]"
  replacement: "_get_float64(idx) / _set_float64(idx, val)"
  root_cause: "Float16 elements are 2 bytes; bitcast[Float32] reads 4 bytes at wrong offsets"
  symptom: "max pooling output contains NaN or Inf"

broader_codebase:
  shared_core_remaining: ~389 patterns (future PRs, was ~395 before pooling fix)
  tests_remaining: ~2458 patterns (future PRs)
```

### Uniform Weight Scaling

```yaml
# For tests using full(shape, scale) -- uniform weights:
random_he_init: "sqrt(2 / fan_in)"  # For random normal weights
uniform_scaling: "1.0 / fan_in"     # For all-same uniform weights
gain_per_layer:
  random_he: "~1.0 (positive/negative cancel)"
  uniform: "fan_in * scale"
  uniform_with_he: "sqrt(2 * fan_in) >> 1.0 (OVERFLOW)"
  uniform_with_1_over_fan: "1.0 (stable)"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #5097 | 101+ bitcast patterns replaced, ASAN clean, VGG16 numerical fix |
| ProjectOdyssey | PR #5175 | Pooling bitcast fix: 6 functions migrated to _get_float64/_set_float64 |
