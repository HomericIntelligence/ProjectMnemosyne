---
name: tensor-numeric-correctness-bugs
description: >-
  Diagnose and fix silent correctness bugs in tensor/array numeric operations.
  Use when: (1) tensor ops produce wrong values for non-contiguous (strided/transposed)
  layouts, (2) a destructor frees an offset view pointer causing ASAN bad-free, (3)
  dtype mismatches silently corrupt values via bitcast (float bits read as int), (4)
  a missing dtype case (bfloat16) causes silent zero reads/writes, (5) multi-dim
  slice ignores step, returning all elements instead of strided subset, (6) IEEE 754
  NaN bit patterns produce inconsistent hashes across runs, (7) a seed parameter is
  declared but never wired to the PRNG causing non-reproducible random tensors,
  (8) byte-pointer arithmetic on a `UnsafePointer[UInt8]` tensor buffer silently
  copies one byte per element regardless of dtype, leaving 3/4 of float32 storage
  uninitialized and quietly corrupting training data.
category: debugging
date: 2026-06-07
version: "1.2.0"
user-invocable: false
history: tensor-numeric-correctness-bugs.history
tags:
  - tensor
  - mojo
  - dtype
  - stride
  - bitcast
  - nan
  - hash
  - asan
  - bad-free
  - view
  - slice
  - bfloat16
  - reproducibility
  - seed
  - numeric-correctness
---

# Skill: Tensor Numeric Correctness Bugs

Silent wrong-value bugs in tensor/array operations in Mojo and Python, covering
stride access, dtype mismatches, view destructors, NaN hash stability, and PRNG
seed wiring.

## Overview

| Attribute | Value |
| ----------- | ------- |
| **Date** | 2026-05-26 |
| **Category** | debugging |
| **Theme** | Silent correctness bugs in tensor/array numeric operations |
| **Outcome** | Canonical covering stride, dtype, memory-safety, hash, and seed patterns |
| **Context** | Absorbed from 7 skills: confusion-matrix-dtype-guard, debugging-slice-view-bad-free-destructor, extensor-bfloat16-fix, fix-non-contiguous-tensor-stride-access, multidim-slice-step-validation, nan-hash-canonicalization, fix-randn-seed-bug |

## When to Use

Use this skill when:

- A tensor copy, flatten, or conversion function produces wrong values for transposed
  or sliced (non-contiguous) tensors, and element access uses `i * dtype_size` flat offset
- ASAN reports `attempting free on address which was not malloc()-ed` and the freed
  address is N bytes inside a larger allocation (slice view bad-free)
- A metric `update()` or operator silently accepts a float dtype where integers are
  required, producing garbage class indices via bitcast
- `ExTensor` operations on `bfloat16` tensors silently produce zeros (missing dtype branch)
- A variadic-arg `__getitem__(*slices)` ignores the `step` field, returning all elements
  for `tensor[::2, :]` instead of every-other-element
- NaN-containing float tensors hash differently across runs despite identical content
  (signaling NaN vs quiet NaN, negative NaN, different NaN payloads)
- Tests using `randn(shape, dtype, seed=N)` produce different values each run because
  the `seed` parameter is declared but never passed to the PRNG
- A batch-extraction or buffer-copy loop walks `AnyTensor._data` (a
  `UnsafePointer[UInt8]`) with `(ptr + i).load()` / `.store()` and the tensor's
  dtype is wider than one byte (float16/bfloat16/float32/float64/int32/int64);
  training data, weights, or activations look "close to correct" but downstream
  training plateaus at chance accuracy or diverges from a matching reference
  implementation

## Verified Workflow

### Quick Reference

```mojo
# 1. Stride-based non-contiguous element copy (as_contiguous / concatenate)
for i in range(numel):
    var src_elem_offset = 0
    var remaining = i
    for d in range(ndim - 1, -1, -1):
        var coord = remaining % shape[d]
        remaining //= shape[d]
        src_elem_offset += coord * tensor._strides[d]
    var src_byte_offset = src_elem_offset * dtype_size
    var dst_byte_offset = i * dtype_size
    for b in range(dtype_size):
        dst_ptr[dst_byte_offset + b] = src_ptr[src_byte_offset + b]

# 2. View destructor guard (AnyTensor.__del__)
if self._refcount[] == 0:
    if not self._is_view:          # Views share parent's allocation
        pooled_free(self._data, self._allocated_size)
    self._refcount.free()          # Refcount is always independently allocated

# 3. Dtype guard before bitcast loop (metric update)
if labels._dtype != DType.int32 and labels._dtype != DType.int64:
    raise Error(
        "update() requires int32 or int64 labels, got " + str(labels._dtype)
    )

# 4. bfloat16 two-step cast (ExTensor I/O)
# Read:  var ptr = (self._data + offset).bitcast[BFloat16](); return Float64(Float32(ptr[]))
# Write: var ptr = (self._data + offset).bitcast[BFloat16](); ptr[] = BFloat16(Float32(value))

# 5. Multi-dim slice step validation
for dim in range(num_dims):
    var step = slices[dim].step.or_else(1)
    if step != 1:
        raise Error(
            "Multi-dimensional slicing does not support step != 1 "
            + "(got step=" + String(step) + " on dimension " + String(dim)
            + "). Use 1D slicing for strided access."
        )

# 6. NaN canonicalization in __hash__
alias CANONICAL_NAN_F64: UInt64 = 0x7FF8000000000000
alias F64_INF_BITS: UInt64 = 0x7FF0000000000000
alias F64_ABS_MASK: UInt64 = 0x7FFFFFFFFFFFFFFF
if (int_bits & F64_ABS_MASK) > F64_INF_BITS:
    int_bits = CANONICAL_NAN_F64

# 7. Wire the seed parameter
from random import random_float64, seed as random_seed
if seed > 0:
    random_seed(seed)
```

### Pattern 1: Non-Contiguous Stride Access

The canonical flat-index bug: `_get_float64(i)` computes `offset = i * dtype_size`
which assumes stride-1 layout. For a transposed (4,3) tensor with strides `[1, 4]`,
element `(0,1)` is at byte offset `1*4*dtype_size`, not `1*dtype_size`.

**Diagnose:**

```bash
grep -n "_get_float64(i)\|_get_float64(src_idx)\|_get_float64(adjusted_idx)" \
  shared/core/shape.mojo
```

Functions to audit: `as_contiguous()`, `concatenate()`, `tile()`, `repeat()`,
`broadcast_to()`, `permute()`, `reshape()`, `stack()`.

**Fix:** Replace with stride-based decomposition (see Quick Reference #1).
Reference implementation lives in `ExTensor.slice()` (extensor.mojo:988-1002).

**Concatenate-specific addition:** Track `result_elem_offset` to accumulate the base
element index in the result for each tensor:

```mojo
var result_elem_offset = offset_bytes // dtype_size
for i in range(t_numel):
    # ... stride decomposition as above ...
    var dst_byte_offset = (result_elem_offset + i) * dtype_size
```

**Concatenate scope warning:** The axis-0 fix above addresses only the `if actual_axis == 0`
branch. The general-axis branch (non-zero `actual_axis`) still uses raw memcpy with flat
offsets — a separate, unaddressed flat-offset bug scoped out by design in issue #4083.
Do not present `concatenate()` as fully fixed for all axes.

**Regression test:** Create `arange(0..12).reshape(3,4)`, transpose, call function,
check all 12 element values against expected transpose. The existing test that only
checks `is_contiguous()` and `_strides` will NOT catch this bug.

**Test isolation via direct `_strides` mutation:** Override `_strides[0]=1`,
`_strides[1]=2` directly on the test tensor to exercise the non-contiguous path
without depending on `transpose_view()` correctness or availability. This avoids
test-order dependencies when `transpose_view()` is under development or unfixed.

### Pattern 2: Slice View Bad-Free Destructor

**ASAN report signature:**

```text
ERROR: AddressSanitizer: attempting free on address which was not malloc()-ed
0x519000001680 is located 512 bytes inside of 1024-byte region
freed by: AnyTensor::__del__ → pooled_free
```

The "N bytes inside of region" proves `_data` was offset (slice view), not independently
allocated. Without ASAN, the crash appears flaky — silent heap corruption accumulates
across ~15-17 test functions before manifesting as abort.

**Build with ASAN to catch immediately:**

```bash
pixi run mojo build --sanitize address -g -I "$(pwd)" -I . \
    -o /tmp/repro <test_file.mojo>
/tmp/repro
```

**Fix:** Add `_is_view` check in `__del__` before `pooled_free` (see Quick Reference #2).

**3-line minimum reproducer:**

```mojo
var data = ones([8, 2, 4, 4], DType.float32)  # 1024 bytes
var batch = data.slice(4, 8)                   # _data = data._data + 512 bytes
# batch.__del__ → pooled_free(offset_ptr) → ASAN: bad-free
```

### Pattern 3: Dtype Guard for Bitcast Misuse

**Vulnerable pattern:**

```mojo
if labels._dtype == DType.int32:
    true_label = Int(labels._data.bitcast[Int32]()[i])
else:
    true_label = Int(labels._data.bitcast[Int64]()[i])  # float32 bits → huge int
```

`float32(1.0)` has IEEE 754 bits `0x3F800000` = 1065353216 as int64 — silently
out-of-range for any `num_classes`. `float32(0.0)` bits are zero, so class-0-only
tests accidentally pass.

**Fix:** Add guard after structural checks, before the per-element loop (Quick Reference #3).
For 2D logit predictions, exempt the 2D path — `argmax()` always returns `int32`.

**Regression test cases:** float32/float64 rejection, int32/int64 acceptance, 2D float
acceptance.

### Pattern 4: Missing bfloat16 in ExTensor I/O

Three sites in `shared/core/extensor.mojo` all need updating together:

1. `_get_dtype_size_static` — add `elif dtype == DType.bfloat16: return 2`
   (falls through to 4-byte default without this, causing wrong offsets)
2. `_get_float64` — add bfloat16 read branch (Quick Reference #4)
3. `_set_float64` — add bfloat16 write branch (Quick Reference #4)

**Checklist for any new float dtype:**

1. `_get_dtype_size_static` — size case
2. `_get_float64` — read branch
3. `_set_float64` — write branch
4. `__setitem__` float condition list
5. Re-enable skipped tests

**Mojo 0.26.1 constraint:** Direct `BFloat16 ↔ Float64` cast produces incorrect values.
Always use Float32 as intermediary (bf16 shares float32's 8-bit exponent).

### Pattern 5: Multi-Dim Slice Step Ignored

The variadic `__getitem__(*slices: Slice)` overload reads `start`/`end` from each
`Slice` but never reads `step`. `tensor[::2, :]` silently returns all elements.

**Find the overload:**

```bash
grep -n "__getitem__(self, \*slices" shared/core/extensor.mojo
```

**Fix:** Insert step-validation loop before the per-dimension computation loop
(Quick Reference #5). Reject bad inputs early — before allocating the result tensor.

Prefer fail-fast (raise Error) over implementing full strided copy unless the caller
explicitly needs strided multi-dim access.

**Tests:** step=2 first dim, step=2 second dim, step=-1, step=3 in 3D, step=1 explicit,
no step (default 1).

### Pattern 6: NaN Hash Canonicalization

After a bitcast-based float hash fix, different NaN bit patterns still produce different
hashes. IEEE 754 defines many valid NaN representations (sign bit, quiet/signaling,
payload bits) — all semantically equal but bit-different.

**NaN detection (Float64 space):** `(bits & 0x7FFFFFFFFFFFFFFF) > 0x7FF0000000000000`

If `_get_float64()` converts all dtypes to Float64 before bitcast, one canonicalization
pass covers float16, float32, float64, and bfloat16 — no per-dtype branches needed.

**Canonical NaN bit patterns:**

| Type | Canonical Quiet NaN | Infinity Bits | NaN Condition |
| ------ | --------------------- | --------------- | --------------- |
| Float16 | `0x7E00` | `0x7C00` | `(bits & 0x7FFF) > 0x7C00` |
| Float32 | `0x7FC00000` | `0x7F800000` | `(bits & 0x7FFFFFFF) > 0x7F800000` |
| Float64 | `0x7FF8000000000000` | `0x7FF0000000000000` | `(bits & 0x7FFFFFFFFFFFFFFF) > 0x7FF0000000000000` |

**Never modify stored tensor data** to canonicalize NaN. The canonicalization is
hash-side only.

### Pattern 7: Unused Seed Parameter

**Symptom:** `randn(shape, dtype, seed=42)` called twice produces different values.

**Root cause:** `seed` parameter declared in function signature and docstring but
no call to `random_seed(seed)` exists in the function body.

**Fix (Quick Reference #7):** Add import and seed call before any `random_float64()`.

**Seed convention:**

| Seed Value | Behavior |
| ------------ | ---------- |
| `seed = 0` | System randomness (non-reproducible) |
| `seed > 0` | Fixed PRNG seed (reproducible) |
| `seed = -1` | Alternative convention for system random |

**Find other occurrences:**

```bash
grep -rn "seed: Int" shared/       # all declarations
grep -rn "random_seed(" shared/    # all actual wiring calls
```

### Pattern 8: Byte-Pointer Arithmetic on Dtype-Wider Tensors

`AnyTensor._data` is `UnsafePointer[UInt8]`. Pointer arithmetic on a byte pointer
moves in byte units, and `.load()` / `.store()` on a `UInt8*` transfers exactly
ONE BYTE — regardless of the tensor's declared dtype. A batch-extraction loop
written as raw byte-pointer math therefore copies only 1 byte per element instead
of `dtype_size` bytes, leaving the remaining `dtype_size - 1` bytes at their
prior value (typically zero from a `zeros()` allocation).

**Vulnerable pattern (from `examples/lenet_emnist/train.mojo` and `train_autograd.mojo`):**

```mojo
# WRONG — byte-pointer arithmetic silently copies 1 byte per element
(batch_images._data + dst_idx).store(
    (train_images._data + src_idx).load()
)
```

For a `float32` tensor (4 bytes/element):

- `dst_idx` and `src_idx` were *element* indices (0, 1, 2, …, N-1)
- The loop ran N iterations and transferred 1 byte each — total N bytes
- The float32 storage needed 4N bytes; the other 3N bytes stayed at `zeros()`

**Downstream effect:** training data is silently "quantized" to a near-garbage
state where only ~1/4 of each float's bits survive. Manual SGD may still
converge (raw SGD on LeNet+EMNIST reached 74% test accuracy on corrupted data)
because enough class signal leaks through. More sensitive paths (autograd,
deeper models, smaller learning rates) asymptote to chance — for 47-class
EMNIST, loss = ln(47) = 3.85 and accuracy ≈ 1/47 ≈ 2.13%.

**Fix:** Replace byte-pointer load/store with dtype-agnostic accessors that
round-trip through `Float64` at the tensor's actual precision:

```mojo
# RIGHT — dtype-agnostic accessor preserves the actual element value
batch_images._set_float64(dst_idx, train_images._get_float64(src_idx))
```

**Diagnose — find vulnerable byte-pointer arithmetic on `_data`:**

```bash
grep -rn "_data + " examples/ src/ shared/ \
  | grep -E "\.(load|store)\("
```

Any hit where the surrounding tensor is not `DType.uint8`/`DType.int8` is suspect.

**Sentinel-based regression check:**

```mojo
# Write a known sentinel, read back via dtype-aware accessor
var t = zeros([4], DType.float32)
t._set_float64(0, 1.25)         # IEEE 754 bits: 0x3FA00000
print(t._get_float64(0))         # must print 1.25
# A 1-byte copy bug shows 0.0 (only low byte 0x00 written)
# or ~1.984e-1 (only high byte 0x3F written) instead
```

**End-to-end convergence check:** Run the affected pipeline for ≥1 epoch
against a known-good reference (e.g., manual SGD vs autograd) on the same
seed and assert per-epoch loss/accuracy match within fp32 reduction-order
noise (typically <0.2 pp). Equality on the first batch is the strongest
signal — if epoch-1 batch-1 loss differs from the reference, the data
pipeline is the prime suspect before any backward op.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Guard dtype check after loop | Placing dtype validation inside the per-element loop | Redundant work; raises on first iteration instead of fast-failing before any loop | Always validate inputs before iterating |
| Validate 2D predictions dtype | Adding dtype guard for pred_classes after the 2D argmax path | argmax() always returns int32, so guard would be dead code | Only validate 1D inputs; document the 2D argmax exemption |
| Generic error message | Using `raise Error("invalid dtype")` without listing accepted types | Forces callers to read source to fix the error | Error messages should include accepted values: "requires int32 or int64, got X" |
| Classified CI crash as JIT overflow | Assumed crash before test output meant JIT compile failure | Re-reading CI logs showed 17 tests PASSED before crash — runtime error, not JIT | Always read the actual CI log output before classifying the failure |
| Assumed same root cause as prior bitcast UAF | Same libKGENCompilerRTShared.so+0x3cb78b offset as earlier UAF | ASAN reported bad-free not heap-use-after-free — different bug | Same crash signature does NOT mean same root cause — ASAN distinguishes them |
| Assumed churn from prior tests was required | Earlier UAF needed ~15 prior functions for heap churn | Running crash test ALONE with ASAN still triggered bad-free | Test the failing function in isolation first — eliminates churn hypothesis |
| Direct BFloat16-to-Float64 cast | `ptr[].cast[DType.float64]()` directly from BFloat16 | Produces incorrect values in Mojo 0.26.1 | Always use Float32 as intermediary for bf16 conversions |
| Only fix I/O branches for bfloat16 | Adding read/write branches without fixing `_get_dtype_size_static` | 4-byte default causes reads/writes at wrong byte offsets | All three sites (size, read, write) must be fixed together |
| Implement full strided copy for multi-dim slice | Build stride-aware multi-dim copy loop instead of raising | Much more complex, increases surface area with no immediate caller need | When issue offers fail-fast vs implement, prefer fail-fast unless strided access is required |
| Add slice step check inside existing loop | Put validation inside per-dimension computation loop | Correct but mixes validation with computation, harder to read | Separate validation from computation: dedicate a pre-loop for fail-fast checks |
| Per-dtype NaN canonicalization | Separate float16/float32/float64 branches in `__hash__` | More complex; `_get_float64()` already unifies all dtypes in Float64 space | If there is a `_get_float64()` helper, canonicalize once in Float64 — no per-dtype branches |
| `math.isnan()` for NaN detection | `isnan(val)` from math module | Works but requires an import; bitwise test is self-contained | Bitwise NaN detection avoids additional imports |
| Canonicalize in stored tensor data | Modify `_data` bytes to replace NaN bits | Violates principle that hash must not mutate stored data; breaks roundtrip fidelity | NaN canonicalization is hash-side only — never mutate tensor data |
| Model state mutation as randn bug cause | Assumed SimpleMLP forward() mutated state causing different outputs | forward() was deterministic; inputs were non-reproducible | Trace actual values in the error message before assuming model-side cause |
| Check only strides after as_contiguous | Verified `_strides` and `is_contiguous()` return value | Strides correctly set on output but input was read with flat offsets | Contiguity of output does not validate correctness of input reads |
| Initial diagnosis: blame conv2d backward | Wrote a chained convergence test with all-uniform weight init (0.05 everywhere) and saw conv kernel gradients come back at 1e-8 magnitude vs FC gradients at 1e-1 — looked like 7 orders of magnitude too small | The all-uniform FC weights made softmax output uniform, the gradient back through FC was algebraically zero, and conv kernels saw only fp32 cancellation noise. Symmetric-init pathology, not a substrate bug. Cost ~30 min misdirection. | Before claiming a magnitude bug in a backward op, verify with asymmetric weight init (e.g., `t[i] = base + i * slope`). Better: compare manual and autograd gradients directly on the same input — L2 diff should be 0.0 if the substrate is correct. |
| Skipped past batch-extraction loop in initial review | Saw identical batch-copy code in `train.mojo` and `train_autograd.mojo`, assumed "same code = same correctness, both work" since manual SGD converged | Same code, same bug — but downstream sensitivity differs. The manual SGD path was robust enough to converge on corrupted data; the autograd path with more allocations and reduction-order variance asymptoted to chance | Code that is identical in two files can still be buggy in both. The path that converges may simply be the path that is more tolerant of the bug. Test the data pipeline end-to-end with known-good inputs, not only via downstream consumers. |
| Trusted that downstream `_get/_set_float64` accessors would protect against bad raw bytes | Forward pass uses `_get_float64` which correctly reads float32, so I assumed it would surface NaN/Inf if the bytes were garbage | `_get_float64` reads exactly the bytes that are there — and zero-filled high bytes of a float32 just decode to denormals or tiny normals. No NaN, no Inf, no error — just numerically valid but signal-free training data | Defensive dtype-correct accessors only protect against type confusion, not against pre-corrupted byte storage. Validate buffer contents directly, e.g., compare `_get_float64(0)` against the known source value before any training starts. |

## Results & Parameters

### ASAN Build Reference

```bash
pixi run mojo build --sanitize address -g -I "$(pwd)" -I . \
    -o /tmp/repro <file.mojo>
/tmp/repro
```

### Non-Contiguous Behavior Without ASAN

| Condition | Behavior |
| ----------- | ---------- |
| With ASAN | Crashes immediately on first bad-free (100% reproducible) |
| Without ASAN, 1 test | Usually passes (corruption too minor to trigger abort) |
| Without ASAN, 15+ tests | Crashes 50-80% of the time (corruption accumulates) |
| Without ASAN, different CI runner | Different heap layout = different crash threshold |
| Smaller test files | Usually pass (fewer tests = less corruption per file) |

### Crash Signature Disambiguation

All three produce identical `libKGENCompilerRTShared.so+0x3cb78b` output:

| Bug | Root Cause | ASAN Report | Our Code? |
| ----- | ----------- | ------------- | ----------- |
| Day 53 bitcast UAF | ASAP destruction frees tensor before bitcast write | heap-use-after-free | No (Mojo compiler bug) |
| Mojo heap corruption | Same bitcast UAF with more churn | heap-use-after-free | No (same Mojo bug) |
| Slice view bad-free | `__del__` frees offset `_data` pointer from slice() | bad-free | Yes (our bug) |

### Byte-Pointer vs Dtype-Pointer Batch Copy

```mojo
# WRONG — byte-pointer arithmetic silently copies 1 byte per element
(batch_images._data + dst_idx).store(
    (train_images._data + src_idx).load()
)

# RIGHT — dtype-agnostic accessor preserves the actual element value
batch_images._set_float64(dst_idx, train_images._get_float64(src_idx))
```

Diagnostic snippet to verify a buffer was copied correctly at the byte level:

```mojo
# Write known sentinel, read back via dtype-aware accessor
var t = zeros([4], DType.float32)
t._set_float64(0, 1.25)  # 0x3FA00000
print(t._get_float64(0))  # must print 1.25, not 0.0 (only low byte 0x00) or 1.984e-1 (only high byte 0x3F)
```

### Key Audit Commands

```bash
# Find flat-index element access in shape ops
grep -n "_get_float64(i)\|_get_float64(src_idx)" shared/core/shape.mojo

# Find stride-unaware variadic slice overloads
grep -n "__getitem__(self, \*slices" shared/core/extensor.mojo

# Find bfloat16 gaps in ExTensor I/O
grep -n "float16\|float32\|float64" shared/core/extensor.mojo | grep -v bfloat16 \
  | grep "_get_dtype_size_static\|_get_float64\|_set_float64"

# Find seed parameters not wired to PRNG
grep -rn "seed: Int" shared/
grep -rn "random_seed(" shared/
```

### Test Strategy Summary

| Pattern | Minimum Tests |
| --------- | --------------- |
| Stride access | All element values on a transposed arange tensor |
| Bad-free | ASAN build of 3-line reproducer; 15+ test monolithic file |
| Dtype guard | float32 rejection, float64 rejection, int32 acceptance, 2D float acceptance |
| bfloat16 I/O | Re-enable skipped bfloat16 test; verify `verify_special_value_invariants` |
| Slice step | step=2 both dims, step=-1, step=3 3D, step=1 explicit, no step |
| NaN hash | +qNaN vs -qNaN, payload variants, sNaN vs qNaN, mixed tensor, shape/dtype sensitivity |
| Seed | Two calls with same seed produce identical tensors; seed=0 is non-reproducible |
| Byte-pointer batch copy | Sentinel round-trip (`_set_float64(0, 1.25)` → `_get_float64(0)` == 1.25); end-to-end convergence matches a known-good reference within fp32 noise (<0.2 pp/epoch) |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issues #3391/#4083, PR #4079/#4865 | Non-contiguous stride access (as_contiguous + concatenate) |
| ProjectOdyssey | PR #5097, ADR-013 | Slice view bad-free destructor |
| ProjectOdyssey | Issue #3686, PR #4769 | Confusion matrix dtype guard |
| ProjectOdyssey | Issue #3300, PR #3903 | ExTensor bfloat16 I/O fix |
| ProjectOdyssey | Issue #4463, PR #4884 | Multi-dim slice step validation |
| ProjectOdyssey | Issue #3382, PR #4058 | NaN hash canonicalization |
| ProjectOdyssey | PR #2980 | Fix unused randn seed parameter |
| ProjectOdyssey | PR #5466 — fix(examples): correct 1-byte-per-element batch copy in lenet_emnist | Bit-for-bit identical loss trajectory with manual baseline post-fix; autograd 5-epoch EMNIST acc 74.24% (matches manual 74.39%) |
