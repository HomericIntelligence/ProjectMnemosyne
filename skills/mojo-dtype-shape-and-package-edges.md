---
name: mojo-dtype-shape-and-package-edges
description: "Canonical edge-case patterns for Mojo dtype handling, shape inference, and package builds: bfloat16/NaN canonicalization, exotic dtype defaults, shape-bound inference, parametric vs runtime dtype, package re-export rules, package-build edges, test patterns for dtype matrices, dtype string serialization. Use when: (1) implementing dtype-aware kernels and dealing with bfloat16/fp16 edge cases, (2) writing shape-bound inference for parametric tensors, (3) building/publishing a Mojo package and dealing with re-exports, (4) constructing dtype/shape test matrices."
category: testing
date: 2026-05-18
version: "1.0.0"
user-invocable: false
verification: verified-local
history: mojo-dtype-shape-and-package-edges.history
tags: [merged, mojo, dtype, shape, package, bfloat16, parametric, testing, stride, slice, spinlock, SIMD, gpu]
---

# Mojo Dtype, Shape, and Package Edge-Case Patterns

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-18 |
| **Objective** | Consolidate 49 Mojo dtype/shape/test/infra edge-case skills as the final sub-PR for M3 |
| **Outcome** | Single canonical reference replacing mojo-026-breaking-changes through noncontiguous-tensor-guard |
| **Verification** | verified-local |
| **History** | [changelog](./mojo-dtype-shape-and-package-edges.history) |

## When to Use

- Implementing or testing dtype-aware kernels (bfloat16, fp16, int narrowing, unsigned wrapping)
- Writing stride-based tensor ops (reshape, slice, transpose, as_contiguous, permute)
- Adding shape-op value-correctness tests (not just numel/dim assertions)
- Debugging flat-index bugs where `_get_float64(i)` ignores `_strides`
- Implementing `__setitem__`, `__getitem__`, `__hash__`, `__bool__`, or `__moveinit__` on ExTensor
- Adding non-contiguous tensor guards to flat-buffer kernels
- Testing spinlock/atomics without CAS support in Mojo
- Migrating from Mojo 0.26.1 to 0.26.3 breaking changes
- Filing upstream Mojo bugs (reproducibility gate)
- Reading binary files in Mojo (IDX/MNIST)
- Making `mojo-format` non-blocking in CI

## Verified Workflow

### Quick Reference

```bash
# Binary file reading (IDX/MNIST) — use read_bytes(), NOT read()
with open(filepath, "r") as f:
    var bytes = f.read_bytes()  # returns List[UInt8]

# bfloat16 pointer — no BFloat16 alias; use SIMD directly
var ptr = UnsafePointer[SIMD[DType.bfloat16, 1]](self._data.bitcast[...])

# Mojo 0.26.3 closure convention: capturing BEFORE raises
fn forward(x: AnyTensor) capturing raises -> AnyTensor: ...

# Float bitcast for __hash__ (avoid Int(val*1e6) overflow)
var local_val = self._get_float64(i)
var bits = UnsafePointer[Float64](to=local_val).bitcast[UInt64]()[]

# dirpath trailing-slash normalization
var normalized = String(dirpath.rstrip("/"))

# Tuple return type in Mojo v0.26.1
fn normalize_slice(...) -> Tuple[Int, Int, Int, Int]:
    return (start, end, step, size)
var s = result[0]  # access with index, not unpacking

# TTAS spinlock (no CAS in Mojo 0.26.x)
fn lock(mut self):
    while True:
        if self._lock_word().load() == 0:
            if self._lock_word().fetch_add(1) == 0:
                return
            _ = self._lock_word().fetch_add(-1)  # undo lost race

fn unlock(mut self):
    _ = self._lock_word().fetch_add(-1)  # NOT store(0) -- store(0) is a data race!

# Non-contiguous kernel guard
fn dispatch_op(x: ExTensor) raises -> ExTensor:
    var x_c = x if x.is_contiguous() else x.as_contiguous()
    return _op_impl(x_c)

# CI: make mojo-format non-blocking
# SKIP=mojo-format pixi run pre-commit run --all-files
```

### Dtype Edge Cases

- `bfloat16`: no `BFloat16` scalar alias -- use `SIMD[DType.bfloat16, 1]`. `_get_float64`/`_set_float64` silently return 0 for bfloat16.
- `Float64(Int64_value)` constructor does not exist -- use `.cast[DType.float64]()`.
- Include `dtype_to_ordinal(self._dtype)` in every hash chain; same shape/values but different dtypes must not collide.
- Hash collision: `Int(val * 1e6)` overflows for large values (1e15) and rounds small values (1e-7) to 0. Use bitcast.

### Slice and Stride Edge Cases

- `_get_float64(i)` uses flat byte offset; it ignores `_strides`. For non-contiguous ops, guard with `is_contiguous()` or call `as_contiguous()`.
- Negative-step slice defaults must depend on step sign. Result size: `ceildiv(start - end, abs_step)` (end exclusive, Python semantics).
- `ExTensor.copy()` / `__copyinit__` is shallow (shared `_data`). For mutation use `_deep_copy()`.
- `^` on `List` in `__moveinit__` loses in-place element mutations -- keep `.copy()` for List fields mutated before move.
- `rstrip("/")` returns `StringSlice`, not `String` -- wrap with `String(...)`.
- N-D slicing via pointer-offset only handles first-axis slices. Use element-wise stride-based copy for N-D.
- N-D first-axis-only fast path: detect when all inner dims are full range; use single `memcpy`.

### Shape Op Value Testing Pattern

Always assert element values (not just numel/dim) for shape ops on non-contiguous inputs. Use `assert_value_at(result, i, expected)` per-element. For non-contiguous test fixtures, transpose with different-sized dims -- same-size dims give identical strides so `is_contiguous()` stays true.

### Test Construction Rules

- Mojo tests: `fn test_*() raises` (not Python `def`); call each in `fn main() raises`.
- Limit: 10 `fn test_` per file -- split when at limit; register split files explicitly in CI yml.
- All tests run in Docker/CI (GLIBC 2.32+ required; host often has 2.31).
- Local gate: `SKIP=mojo-format pixi run pre-commit run --all-files`.
- Parametric helpers go in `shared/testing/assertions.mojo`; re-export via `tests/shared/conftest.mojo`.
- ConfusionMatrix requires `DType.int32` or `DType.int64` labels (not float).
- DataLoader constructor: positional args only (no keyword args in Mojo struct constructors).
- Step function for `run_epoch_with_batches`: must be named top-level `fn`, not closure.

### Mojo 0.26.3 Breaking Changes

- Closure convention: `capturing` BEFORE `raises` in fn type annotations.
- `substr()` removed -- use `String(x[byte=start:end])`.
- `ImplicitlyDestructible` trait required for types used in `List` fields.
- `mojo-format` may crash on new syntax -- add `continue-on-error: true` or `SKIP=mojo-format`.

### Upstream Bug Filing Gate

Run a minimal reproducer just-in-time on the pinned Mojo version. 100% determinism required. Never file from memory or stale ADRs. Not upstream unless it reproduces locally with a minimal script.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `^` transfer of List in `__moveinit__` | Replace `.copy()` with `^` for performance | In-place element mutations (e.g. `_shape[axis]=val`) are lost | Keep `.copy()` for List fields mutated in-place before move |
| `store(0)` in spinlock unlock | `Atomic.store(0)` instead of `fetch_add(-1)` | Races with in-flight `fetch_add(-1)` undos: counter goes negative, threads deadlock | Unlock MUST use `fetch_add(-1)` to match the TTAS protocol |
| Pointer-offset view for N-D slicing | `self.copy()` + `result._data.offset(bytes)` | Only handles first-axis; inner gaps invisible to pointer arithmetic | Use element-wise stride-based copy for N-D |
| `open(filepath, "rb")` for binary files | Python-style binary mode | Mojo 0.26.3 raises `"Invalid open mode"` | Use `f.read_bytes()` with plain `"r"` mode |
| `-> (Int, Int)` tuple return annotation | Python-style parenthesized tuple in `fn` signature | Compiler error: `no matching function in initialization` | Use `-> Tuple[Int, Int]` in annotation; `return (v1, v2)` in body |
| `UnsafePointer.address_of(temporary)` | `UnsafePointer.address_of(self._get_float64(i))` | Dangling pointer; `address_of` is not a static method in Mojo 0.26.1 | Assign to named local first; use `UnsafePointer[T](to=val)` |
| `transpose(0,1)` on same-sized dims | `(1,1,4,4)` tensor transposing N and C | N=C=1 gives identical strides -- `is_contiguous()` stays true | Use dims of different sizes; for NCHW N=C=1, transpose spatial dims |
| `fn(AnyTensor) raises capturing -> AnyTensor` | Wrong keyword order in closure type | "expected a type, not a value" | Correct: `fn(AnyTensor) capturing raises -> AnyTensor` |
| `Int(val * 1e6)` for float hash | Multiply by 1e6, truncate | Overflows for large values; rounds small values to 0 | Bitcast via `UnsafePointer[Float64](to=val).bitcast[UInt64]()[]` |
| Uniform `grad_output=ones` for backward tests | All-ones upstream gradient | Algebraic cancellation makes key terms vanish | Use non-uniform `grad_output` for normalization backward tests |
| Full numerical gradient check for `batch_size=1` | `compute_numerical_gradient` with epsilon=1e-3 | Variance near 0 causes catastrophic amplification | Finiteness-only for batch_size=1; full check for batch_size>=2 |
| `assert_equal` (non-fuzzy) on Float64 metrics | Exact equality for val_accuracy | Float accumulation precision | Use `assert_almost_equal` or `assert_greater(x, 0.0)` |
| Helper function placed after `main()` | New test fn after `fn main()` block | Mojo treats post-main code as dead | Always place test helpers before `main()` |
| `Float64(Int64_value)` constructor | Implicit Scalar conversion | Not supported in Mojo 0.26.1 | Use `.cast[DType.float64]()` |
| `Tuple.__del__` for element cleanup | Return `.slice()` views from `Dataset.__getitem__` | Mojo 0.26.x Tuple does NOT call `__del__` on non-trivial elements | Return `.clone()` (owned deep copies) from `__getitem__` |
| Independent refcount on slice view | View with own refcount=1 | ASAP destruction frees parent while view still holds pointer into freed memory | Views MUST share parent's refcount to extend parent lifetime |

## Results & Parameters

**Mojo version**: 0.26.1 / 0.26.3

**Gradient tolerances**: Layer norm `epsilon=1e-4`, `atol=1e-5`; Batch norm `epsilon=1e-3`, `atol=1e-4`.

**Float close**: `rtol=1e-5`, `atol=1e-8`; NaN: `Float64(0.0)/Float64(0.0)`; Inf: `Float64(1.0)/Float64(0.0)`.

**Dtype test matrix pattern**:

```mojo
for dtype in get_test_dtypes():
    var t = zeros(shape, dtype)
    t._set_float64(0, Float64(3.14))
    assert_almost_equal(t._get_float64(0), Float64(3.14), tolerance=1e-5)
```

**Narrowing cast semantics**: `UInt64 -> UInt8` truncates to low 8 bits (`value % 256`). Test boundary values: `0`, `255`, `256`, `MAX`.
