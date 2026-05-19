---
name: mojo-dtype-shape-and-package-edges
description: "Canonical edge-case patterns for Mojo dtype handling, shape inference, and package builds: bfloat16/NaN canonicalization, exotic dtype defaults, shape-bound inference, parametric vs runtime dtype, package re-export rules, package-build edges, test patterns for dtype matrices, dtype string serialization. Use when: (1) implementing dtype-aware kernels and dealing with bfloat16/fp16 edge cases, (2) writing shape-bound inference for parametric tensors, (3) building/publishing a Mojo package and dealing with re-exports, (4) constructing dtype/shape test matrices."
category: testing
date: 2026-05-18
version: "1.0.0"
user-invocable: false
verification: verified-local
history: mojo-dtype-shape-and-package-edges.history
tags: [merged, mojo, dtype, shape, package, bfloat16, parametric]
---

# Mojo Dtype, Shape, and Package Edges

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-18 |
| **Objective** | Consolidate 49 Mojo dtype/shape/package edge-case skills (M3 sub-PR 4/4, FINAL) |
| **Outcome** | Single reference covering: dtype handling, tensor slicing/shape ops, noncontiguous layouts, test patterns, GPU fundamentals, spinlock, binary I/O, and more |
| **Verification** | verified-local |
| **History** | [mojo-dtype-shape-and-package-edges.history](./mojo-dtype-shape-and-package-edges.history) |

## When to Use

1. Implementing dtype-aware kernels with bfloat16/fp16/int edge cases
2. Writing shape-bound or stride-aware tensor operations
3. Constructing dtype/shape test matrices (narrowing cast, wrapping, bitwise NOT)
4. Debugging noncontiguous tensor bugs (reshape, slice, stride manipulation)
5. Implementing or fixing ExTensor dunder methods (`__setitem__`, `__hash__`, `__getitem__`)
6. Migrating Mojo code after a version bump (0.26.1 → 0.26.3 breaking changes)
7. Implementing a spinlock or atomic primitive in Mojo without CAS support
8. Reading binary files in Mojo; avoiding the UTF-8 `f.read()` trap
9. Building, formatting, or filing upstream Mojo bugs reproducibly
10. GPU kernel programming with the MAX GPU API

## Verified Workflow

### Quick Reference

```bash
# Check all unique compile error categories first
pixi run mojo package -I . shared -o /tmp/shared.mojopkg 2>&1 | grep ": error:" | sort -u

# Check deprecation warnings separately
pixi run mojo package -I . shared -o /tmp/shared.mojopkg 2>&1 | grep ": warning:" | sort -u

# Skip mojo-format locally (GLIBC mismatch on older hosts)
SKIP=mojo-format pixi run pre-commit run --all-files --show-diff-on-failure

# Run pre-commit excluding mojo-format + advisory format check
SKIP=mojo-format pixi run pre-commit run --all-files
pixi run pre-commit run mojo-format --all-files || echo "mojo-format advisory only"
```

### Dtype Edge Cases

**bfloat16 — no `BFloat16` scalar alias:**

```mojo
# WRONG: BFloat16 alias does not exist in Mojo stdlib
var p: BFloat16  # compile error

# CORRECT: use SIMD with width 1
var p: SIMD[DType.bfloat16, 1]
```

**Scalar type conversions — always use `.cast[]()`, not constructor:**

```mojo
# WRONG: no implicit Scalar[int64] -> Scalar[float64]
var f = Float64(my_int64_scalar)  # compile error

# CORRECT
var f = my_int64_scalar.cast[DType.float64]()
```

**NaN and infinity — arithmetic, not literals:**

```mojo
var nan = Float64(0.0) / Float64(0.0)
var inf = Float64(1.0) / Float64(0.0)
var neg_inf = Float64(-1.0) / Float64(0.0)
```

**assert\_close\_float tolerance formula:** `|a - b| <= atol + rtol * |b|`
Default: `atol = 1e-8`, `rtol = 1e-5`.

**Hash with float fields — use bitcast, not arithmetic:**

```mojo
# WRONG: overflow for large values, collision for small
var bits = Int(val * 1000000.0)

# CORRECT: assign to local first (avoid dangling pointer), then bitcast
var local_val = self._get_float64(i)
var ptr = UnsafePointer[Float64](to=local_val)
update_hash(ptr.bitcast[UInt64]()[])
```

Always include `dtype_to_ordinal(self._dtype)` in hash chain to avoid collisions between same-data different-dtype tensors.

**Binary file I/O — use `read_bytes()`, not `read()`:**

```mojo
# WRONG: crashes on non-UTF-8 bytes (e.g. IDX/MNIST magic number 0x00)
var s = f.read()
# WRONG: mode "rb" does not exist in Mojo 0.26.3
with open(filepath, "rb") as f: ...

# CORRECT
with open(filepath, "r") as f:
    var bytes = f.read_bytes()
```

**UnsafePointer address-of — use constructor, not static method:**

```mojo
# WRONG: address_of is not a method on UnsafePointer type in Mojo 0.26.1
UnsafePointer.address_of(local_val).bitcast[UInt64][]

# CORRECT
UnsafePointer[Float64](to=local_val).bitcast[UInt64][]
```

### Shape and Slice Operations

**Noncontiguous tensor test fixture — direct stride mutation:**

```mojo
var shape = List[Int]()
shape.append(2); shape.append(3)
var t = ExTensor(shape, DType.float32)
for i in range(6):
    t._set_float64(i, Float64(i))
# Overwrite to column-major strides
t._strides[0] = 1
t._strides[1] = 2
assert_false(t.is_contiguous())
```

**Noncontiguous reshape — inline stride loop, not `as_contiguous()` chain:**

```mojo
# Expected values must be computed from actual stride formula, not intuition
# Use _data pointer + manual byte arithmetic for dtype-agnostic copy
# List literal syntax: var x: List[Float64] = [0, 4, 8, ...]
```

**N-D `__getitem__(Slice)` — extend to multidim:**

```text
1. Remove rank guard ("only supported for 1D tensors")
2. Keep start/end/step/result_size computation (axis-0 semantics)
3. In else branch: use _strides[0] * dtype_size as slab_bytes
4. Result shape: [result_size, shape[1], shape[2], ...]
5. Create new test file (≤10 fn test_ per file limit)
```

**Negative-step slices — step-sign-dependent defaults:**

```mojo
# For [::-1], defaults must be based on step sign BEFORE normalization
# Python end is always exclusive; use ceildiv(start - end, neg_step)
# with end clamped to -1 for full reverse
```

**Contiguous fast-path for N-D slice:**

```mojo
# Fast-path condition: all dims use full range (starts[dim]==0, result_shape[dim]==self._shape[dim])
# Insert after result_numel, dtype_size, src_ptr, dst_ptr are declared
# Only guard what is actually implemented (step support is not yet implemented for N-D)
```

**Shallow copy / view hazard:**

```mojo
# __copyinit__ for ExTensor is explicitly shallow — shares _data pointer
# Mutation via shallow copy mutates caller's tensor
# Restoration after loop does NOT help (writes to same shared buffer)
# Fix: always use .copy() (deep copy) before mutating
```

**Tuple destructor / clone pattern (Mojo 0.26.x):**

```mojo
# Tuple.__del__ does NOT call __del__ on non-trivial element types in 0.26.x
# WRONG: return .slice() views from __getitem__ — ASAN pooled_alloc leak
# WRONG: give slice views independent refcount — heap-use-after-free (ASAP destruction)
# WRONG: _ = dataset lifetime extension — fragile, breaks encapsulation

# CORRECT: return .clone() from Dataset.__getitem__
fn __getitem__(self, idx: Int) raises -> Tuple[AnyTensor, AnyTensor]:
    return (self.data.slice(...).clone(), self.labels.slice(...).clone())
```

### Mojo 0.26.3 Breaking Changes (Key Fixes)

| Change | Old Syntax | Correct 0.26.3 Syntax |
| ------- | ----------- | ----------------------- |
| Capturing closure order | `fn(T) raises capturing -> T` | `fn(T) capturing raises -> T` |
| Empty capture list | `unified {}` | `capturing` |
| `substr` removed | `s.substr(i, n)` | `String(s[byte=i:i+n])` |
| `__moveinit__` with `deinit` | `self.name = other.name^` | Remove `__moveinit__`; use auto-move |
| `ImplicitlyCopyable` on `AnyTensor` | Drop trait for `List[T]` | Prefer `InlineArray` fix or add `ImplicitlyDestructible` |

### Atomic SpinLock (TTAS Pattern — no CAS in Mojo 0.26.x)

```mojo
# Mojo Atomic[DType.int64] has NO compare_exchange; use TTAS double-check lock
# lock(): spin while counter != 0; then fetch_add(+1); if result != 1, fetch_add(-1) and retry
# unlock(): MUST use fetch_add(-1) — store(0) is a data race under TTAS contention
# Counter invariant: exactly 1 when held, 0 when free
# Counter must never go below 0 or above 1 (all excess increments cleaned up in lock())
```

### Test Patterns

**Dtype/shape test matrix structure:**

```mojo
# Keep ≤10 fn test_ per file; split across part1/part2/... files
# For 4 integer types × 4 cases = 16 tests → 2 files of 8
# Enumerate all split filenames explicitly in CI yml (no glob patterns)
# Place helper functions BEFORE fn main()
```

**Boundary / out-of-bounds tests:**

```mojo
fn test_getitem_out_of_bounds() raises:
    var t = ExTensor(...)
    var raised = False
    try:
        _ = t[999]
    except:
        raised = True
    assert_true(raised, "Expected out-of-bounds error")
```

**Exception message assertion:**

```mojo
fn test_specific_error_message() raises:
    var raised = False
    try:
        _ = risky_call()
    except e:
        assert_equal(String(e), "expected message text")
        raised = True
    assert_true(raised, "Expected exception was not raised")
```

**Value-correctness assertions after shape ops:**

```mojo
# Use _get_float64(flat_index) as the test oracle — lowest-level reader
# For non-uniform outputs use assert_value_at in a loop
# For broadcast: nested row/col loop with flat index row * cols + col
# For tile/repeat: verify individual indices, not assert_all_values
```

**Numerical gradient test patterns:**

```mojo
# ALWAYS use non-uniform grad_output for normalization backward tests
# Uniform all-ones causes sum(x_hat)=0 cancellation — masks bugs
# Layer norm: epsilon=1e-4, atol=1e-5
# Batch norm: epsilon=1e-3, atol=1e-4
# When batch_size=1: finiteness-only assertions (variance near 0 = FD instability)
# Perturb the exact parameter whose gradient you are testing
```

**GPU programming (MAX GPU API):**

```mojo
# Kernel launch pattern: DeviceContext, grid_dim, block_dim
# Data transfer: HostBuffer -> DeviceBuffer via copy_to_device()
# Synchronize before reading results: ctx.synchronize()
# Prefer SIMD width = simdwidthof[dtype]() for compute-bound kernels
```

### Path and Format Utilities

**Trailing-slash normalization:**

```mojo
# rstrip returns StringSlice, not String — wrap explicitly
var clean = String(dirpath.rstrip("/"))
create_directory(clean + "/" + filename)
```

**mojo-format non-blocking CI:**

```yaml
- name: Run pre-commit (excluding mojo-format)
  run: SKIP=mojo-format pixi run pre-commit run --all-files --show-diff-on-failure
- name: mojo-format advisory
  continue-on-error: true
  run: pixi run pre-commit run mojo-format --all-files || echo "::warning::non-blocking"
```

**NOTE → docstring conversion rules:**

- Only convert NOTEs in production code describing API constraints
- Module-level comments are not docstrings in Mojo — keep as plain comment
- Docstring examples are scanned by pre-commit hooks — use `append()` not `List[T](x,y)` style
- Do not add Note: to every function — only when callers need to know the constraint

### Upstream Bug Filing Standard

Before filing any Mojo bug against modular/modular:

1. Write a minimal standalone `.mojo` reproducer
2. Confirm 100% deterministic on the current pinned version
3. Verify just-in-time (not from memory or old ADRs)
4. Reproduce locally with a minimal script (not CI-only failures)
5. Non-deterministic CI failures are environment issues, not Mojo bugs

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `BFloat16` scalar alias | Used `BFloat16` type similar to `Float16`/`Float32` | Mojo stdlib has no `BFloat16` scalar alias | For bfloat16 use `SIMD[DType.bfloat16, 1]` |
| `Float64(Int64_val)` | Passed `Int64` scalar to `Float64()` constructor | No implicit `Scalar[int64]` → `Scalar[float64]` in Mojo 0.26.1 | Use `.cast[DType.float64]()` for Scalar conversions |
| `UnsafePointer.address_of()` static method | Called as static method on type | `address_of` is not a static method in Mojo 0.26.1 | Use `UnsafePointer[T](to=val)` constructor |
| `Int(val * 1e6)` for float hash | Multiply float by 1e6 to get integer hash bits | Overflows Int64 for large values; collides for small values (`0.1` rounds to 0) | Use bitcast to UInt64 to preserve all 64 IEEE bits |
| Taking address of return value | `UnsafePointer.address_of(self._get_float64(i))` | Dangling pointer — temporary has no stable address | Assign to named local variable first |
| `open(filepath, "rb")` | Binary open mode as in Python | Mojo 0.26.3 raises "Invalid open mode" — only `r`, `w`, `rw`, `a` are valid | Use `f.read_bytes()` with mode `"r"` |
| `f.read()` for binary files | Default text read of binary file | Crashes with "Cannot construct a String from invalid UTF-8 data" | Use `f.read_bytes()` — returns `Bytes`, not `String` |
| Pointer-offset view for N-D slice | `result._data = self._data.offset(offset_bytes)` | Only handles first-axis slices; inner dimension gaps invisible to pointer arithmetic | N-D slicing is inherently noncontiguous; element-wise copy required |
| `store(0)` for spinlock unlock | `Atomic.store(0)` in unlock path | Races with `fetch_add(-1)` undo from other threads; drives counter to -1; all threads deadlock | Unlock MUST be `fetch_add(-1)` for TTAS spinlock |
| Naive `fetch_add` lock + `fetch_sub` unlock | `lock`: `fetch_add(1)` unconditionally; `unlock`: `fetch_sub(1)` | Under contention, multiple in-flight increments; `fetch_sub` drives counter below 0 | Counter must be exactly 1 when held; TTAS pattern required |
| CAS translation from C++ | `compare_exchange_weak(&expected, 0, 1)` | Mojo `Atomic[DType.int64]` has no `compare_exchange` in 0.26.x | Check Mojo Atomic API; use TTAS double-check pattern |
| `^` transfer in `__moveinit__` after in-place mutation | `self.shape = other.shape^` after `result._shape[axis] = ...` | `^` on List in `__moveinit__` does not preserve in-place mutations made before the move (Mojo 0.26.1 bug) | Only use `^` on List when no in-place mutations were made before the move |
| Return `.slice()` views from `Dataset.__getitem__` | Shared parent refcount through view | Mojo 0.26.x Tuple `__del__` does NOT call element destructors; refcount never reaches 0; ASAN `pooled_alloc` leak | Return `.clone()` from any `__getitem__` returning into a Tuple |
| Independent refcount on slice view | Created view with refcount=1 instead of shared | ASAP destruction frees parent before view is done; `heap-use-after-free` | Views MUST share parent refcount to prevent ASAP early-free |
| `fn(AnyTensor) raises capturing -> T` | Used `capturing` after `raises` in closure type | "expected a type, not a value" — wrong ordering | Correct: `fn(T) capturing raises -> T` |
| `unified {}` empty capture list | Used as capture keyword | "Could not infer capture convention" | Use `capturing` keyword instead |
| `__setitem__` overloads for `obj[i]=val` | Added `__setitem__` overloads expecting subscript dispatch | Mojo decomposes `obj[i]=val` into `__getitem__(i)` lvalue + assign — `__setitem__` is never called | Add matching `__getitem__` overload; `__setitem__` is not used by subscript assignment |
| `Float32()` constructor in `@parameter fn` | Wrapped RHS in `Float32()` inside `parallelize[]` | `Float32()` constructor raises; `@parameter fn` closures cannot raise | Use non-raising `_set_float64` internal method for parallel contexts |
| `rstrip("/")` result used directly as `String` | `create_directory(dirpath.rstrip("/"))` | `rstrip` returns `StringSlice`, not `String`; type mismatch | Wrap: `String(dirpath.rstrip("/"))` |
| Uniform `grad_output=ones` for normalization backward | Used all-ones upstream gradient | `sum(x_hat)=0` by normalization — last backward term vanishes, masking bugs | Always use non-uniform `grad_output` for batch norm / layer norm tests |
| Filing Mojo bugs from memory or old ADRs | Drafted issue from recalled crash, or cited ADR written for 0.26.1 | Bug may be fixed; ADR may be stale; maintainers reject non-reproducible issues | Always run the reproducer just-in-time before filing |
| Non-deterministic CI failure → upstream bug | JIT crash at \~40-60% CI hit rate; began writing issue template | Non-deterministic = environment issue, not a Mojo language bug | 100% determinism is a hard requirement for upstream bug filing |
| `List[T](x, y)` constructor in docstring examples | Used variadic List init in docstring code blocks | `check-list-constructor` pre-commit hook scans ALL Mojo source including docstrings | Use `append()` style in docstring examples |
| `#3236` at line start in prose | Wrote "during the \#3236 development cycle" in markdown prose | MD018: markdownlint treats `#N` at line start as a malformed ATX heading | Escape with `\#3236` or rephrase as "issue-3236" |
| Converting all NOTE comments to docstrings | Converted every `# NOTE:` in the repo | Test files have NOTE-style skip explanations that should not become docstrings | Only convert NOTEs in production code describing API constraints |
| Adding test after `fn main()` | Placed helper test function after the `main()` block | Mojo treats it as dead code outside any callable | Always place helper test functions before `main()` |
| `transpose(0, 1)` on `(1,1,4,4)` NCHW | Create non-contiguous tensor by swapping N and C | N=1, C=1 — same size → strides equal after swap → `is_contiguous()` returns true | Only transpose dims of **different sizes**; for N=C=1 use spatial dims (H, W) |
| `as_contiguous()` inside noncontiguous fix | Materialize contiguous copy before reshape | Would allocate extra tensor; also `as_contiguous()` had the same flat-index bug | Implement stride loop inline; do not chain through another buggy function |
| `Tuple return -> (T1, T2)` | Changed validate to return `(avg_loss, accuracy)` | Deprecated in Mojo guidelines; zero precedent in codebase | Use a second-pass accumulation instead |
| `SKIP=hook-id` vs `--no-verify` | Considered `--no-verify` to bypass all hooks | CLAUDE.md explicitly prohibits `--no-verify` | Always use `SKIP=specific-hook-id` |
| Running `mojo` locally on Debian 10 / GLIBC \< 2.32 | `pixi run mojo test tests/...` on older host | GLIBC 2.32/2.33/2.34 not found — Mojo binary requires newer libc | Mojo tests only run in Docker/CI; pre-commit hooks + CI are the local gate |

## Results & Parameters

### ExTensor Quick Reference

| Operation | Pattern |
| --------- | ------- |
| Scalar conversion | `.cast[DType.float64]()` |
| bfloat16 pointer | `SIMD[DType.bfloat16, 1]` |
| Float hash bits | `UnsafePointer[Float64](to=local).bitcast[UInt64][]` |
| Deep copy | `.copy()` |
| Shallow copy warning | `__copyinit__` shares `_data` pointer |
| Subscript assign | Requires matching `__getitem__` lvalue |

### Test File Limits

- Max 10 `fn test_` per file; split into part1/part2/... as needed
- CI yml: enumerate filenames explicitly (no glob patterns)
- Assertion helpers: `assert_true`, `assert_almost_equal`, `assert_equal` (from conftest)
- For float comparisons: `assert_almost_equal(val, expected, tolerance)`
- For hash stability: assert equality between two calls, not against a magic constant

### GPU Programming Checklist

1. Use `simdwidthof[dtype]()` for SIMD width selection
2. Synchronize before reading results: `ctx.synchronize()`
3. Transfer: `HostBuffer` → `DeviceBuffer` via `copy_to_device()`
4. Grid/block dim: tune to hide memory latency

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectOdyssey | M3 skill-merge swarm, 2026-05-18 | 49 source skills, all verified-local individually |
