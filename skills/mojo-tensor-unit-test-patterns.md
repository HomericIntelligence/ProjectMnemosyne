---
name: mojo-tensor-unit-test-patterns
description: >-
  Test patterns specific to Mojo tensor and operator implementations. Use when:
  (1) activating TODO-guarded __str__/__repr__ placeholder tests in Mojo,
  (2) adding dtype-aware string/repr formatting for integer or bool types,
  (3) writing BFloat16 NaN canonicalization or regression tests,
  (4) adding UInt bitwise NOT or overflow/wrap-around boundary tests,
  (5) closing value-correctness gaps in structural tensor tests,
  (6) fixing view vs copy semantics mismatches in slice tests,
  (7) replacing hardcoded /tmp paths with unique per-run paths,
  (8) re-enabling NOTE-disabled or TODO-stubbed Mojo test files,
  (9) annotating pass-only placeholder tests against staleness,
  (10) resolving TODO(#N) markers after a blocking issue closes.
category: testing
date: 2026-05-19
version: "1.0.0"
user-invocable: false
history: mojo-tensor-unit-test-patterns.history
tags:
  - mojo
  - tensor
  - extensor
  - dtype
  - bfloat16
  - uint
  - view
  - copy
  - str
  - repr
  - placeholder
  - todo
  - re-enable
---

# Skill: Mojo Tensor Unit Test Patterns

## Overview

| Attribute | Value |
| ----------- | ------- |
| **Date** | 2026-05-19 |
| **Category** | testing |
| **Language** | Mojo v0.26.1+ |
| **Objective** | Canonical reference for all Mojo tensor test patterns: string/repr, BF16, UInt arithmetic, view/copy semantics, placeholder management, and test re-enablement |
| **Outcome** | Merged from 12 skills covering ExTensor, DType, UInt, and test lifecycle patterns |
| **Context** | ProjectOdyssey — `shared/core/extensor.mojo`, `tests/shared/core/` |

## When to Use

Use this skill when working in a Mojo tensor/operator test suite and any of these apply:

1. A test file has `pass  # Placeholder` stubs guarded by `# TODO(#NNNN)` comments
2. `ExTensor.__str__` or `__repr__` renders integer values with decimals or bools as 0.0/1.0
3. BFloat16 NaN hash values are inconsistent across different NaN bit patterns
4. A dtype-dispatched function lacks a bfloat16 branch (silent no-op or garbage read)
5. UInt bitwise NOT (`~`) or overflow/wrap-around tests are missing from the test suite
6. A structural test checks only `is_contiguous()` and `_strides` but skips element values
7. A slice test asserts `_is_view == True` on `__getitem__(Slice)` (which returns a copy)
8. A test writes to a hardcoded `/tmp/<fixed-name>` path that can persist across runs
9. A `.mojo` test file has `NOTE: temporarily disabled` or only prints "SKIPPED"
10. A tracking issue documents `TODO(#N)` markers and issue #N is now closed

Do NOT use when:
- Tests are skipped due to an active, unfixed compiler bug — document the blocker instead
- Tests require external resources not available in CI
- The blocking upstream issue is still open — verify `gh issue view N --json state` first

## Verified Workflow

### Quick Reference

| Pattern | Key Action | File(s) Typically Changed |
| --------- | ------------ | -------------------------- |
| Activate `__str__`/`__repr__` stubs | Implement `Stringable`/`Representable` on struct | `extensor.mojo`, `test_utility.mojo` |
| Dtype-aware str/repr formatting | Add `_format_element()` helper, dispatch by `DType` | `extensor.mojo`, `test_utility.mojo` |
| BF16 NaN canonicalization | Raw bit manipulation in `_get_float64` BF16 branch | `extensor.mojo`, `test_utility.mojo` |
| BF16 regression (silent no-op) | Three-part test: zero-guard, write zero-guard, round-trip | `test_extensor_getset_<fn>.mojo` |
| UInt bitwise NOT tests | Create standalone `test_uint_bitwise_not.mojo` | new test file + CI YAML |
| UInt overflow/wrap tests | Extend `test_unsigned.mojo` with 15 tests | `test_unsigned.mojo` |
| Value-correctness gap | Append `assert_almost_equal` after stride assertions | `test_utility.mojo` |
| View vs copy semantics | Use `tensor.slice(a, b)` for write-through; `tensor[a:b]` is a copy | test file |
| Unique `/tmp` path | `from time import perf_counter_ns` + string suffix | test file |
| Re-enable disabled tests | Determine disable pattern, check blockers, write/uncomment tests | stub test file |
| Annotate stale placeholders | Add `# TODO(#N)` + concrete spec to docstring | test files |
| Resolve blocked TODOs | Verify blocking issue closed, cherry-pick or implement, enable tests | test files |

---

### Pattern 1 — Activate `__str__`/`__repr__` Placeholder Tests

#### Step 1: Confirm implementation status

```bash
grep -rn "fn __str__\|fn __repr__" shared/core/extensor.mojo
```

If absent, implementation is needed (Steps 2–3). If present, skip to Step 4.

#### Step 2: Add traits to struct declaration

```mojo
# Before
struct ExTensor(Copyable, ImplicitlyCopyable, Movable, Sized):

# After
struct ExTensor(Copyable, ImplicitlyCopyable, Movable, Sized, Stringable, Representable):
```

#### Step 3: Implement `__str__` and `__repr__`

Use `_get_float64(index)` for element access (handles all dtypes via cast):

```mojo
fn __str__(self) -> String:
    """Human-readable string representation."""
    var result = String("ExTensor([")
    for i in range(self._numel):
        if i > 0:
            result += ", "
        result += String(self._get_float64(i))
    result += "], dtype=" + String(self._dtype) + ")"
    return result

fn __repr__(self) -> String:
    """Detailed representation for debugging."""
    var shape_str = String("[")
    for i in range(len(self._shape)):
        if i > 0:
            shape_str += ", "
        shape_str += String(self._shape[i])
    shape_str += "]"
    var result = String("ExTensor(shape=") + shape_str
    result += ", dtype=" + String(self._dtype)
    result += ", numel=" + String(self._numel)
    result += ", data=["
    for i in range(self._numel):
        if i > 0:
            result += ", "
        result += String(self._get_float64(i))
    result += "])"
    return result
```

#### Step 4: Activate placeholder tests

```mojo
fn test_str_readable() raises:
    var t = arange(0.0, 3.0, 1.0, DType.float32)
    var s = String(t)
    assert_equal(s, "ExTensor([0.0, 1.0, 2.0], dtype=float32)", "__str__ format")

fn test_repr_complete() raises:
    var shape = List[Int]()
    shape.append(2)
    shape.append(2)
    var t = ones(shape, DType.float32)
    var r = repr(t)
    assert_equal(
        r,
        "ExTensor(shape=[2, 2], dtype=float32, numel=4, data=[1.0, 1.0, 1.0, 1.0])",
        "__repr__ format",
    )
```

---

### Pattern 2 — Dtype-Aware str/repr Formatting (Integer and Bool)

When `ExTensor.__str__` renders int32 as `"1.0"` or bool as `"0.0"`, add a
`_format_element` helper that dispatches by dtype:

```mojo
fn _format_element(self, i: Int) -> String:
    """Format a single element based on dtype."""
    if self._dtype == DType.bool:
        return "True" if self._get_int64(i) != 0 else "False"
    elif (
        self._dtype == DType.int8
        or self._dtype == DType.int16
        or self._dtype == DType.int32
        or self._dtype == DType.int64
        or self._dtype == DType.uint8
        or self._dtype == DType.uint16
        or self._dtype == DType.uint32
        or self._dtype == DType.uint64
    ):
        return String(self._get_int64(i))
    else:
        return String(self._get_float64(i))
```

Use explicit `== DType.xxx` comparisons — the codebase uses runtime enum comparisons
everywhere; do NOT use `dtype.is_integral()`.

Update `__str__` and `__repr__` to call `self._format_element(i)` instead of
`String(self._get_float64(i))`.

Test using `zeros(shape, dtype) + t[i] = value`:

```mojo
fn test_str_int32_no_decimals() raises:
    var shape = List[Int]()
    shape.append(3)
    var t = zeros(shape, DType.int32)
    t[1] = 1.0
    t[2] = 2.0
    assert_equal(String(t), "ExTensor([0, 1, 2], dtype=int32)", "__str__ int32")

fn test_str_bool_true_false() raises:
    var shape = List[Int]()
    shape.append(3)
    var t = zeros(shape, DType.bool)
    t[1] = 1.0
    assert_equal(
        String(t), "ExTensor([False, True, False], dtype=bool)", "__str__ bool"
    )
```

---

### Pattern 3 — BFloat16 NaN Canonicalization Test

#### Diagnose the conversion path

```mojo
# WRONG — numeric cast may silently canonicalize NaN bit patterns
elif self._dtype == DType.bfloat16:
    var ptr = (self._data + offset).bitcast[BFloat16]()
    return Float64(Float32(ptr[]))
```

#### Fix with raw bit manipulation

BF16 bits map directly to the upper 16 bits of Float32:

```mojo
# CORRECT — preserves all NaN mantissa bits
elif self._dtype == DType.bfloat16:
    var raw_ptr = (self._data + offset).bitcast[UInt16]()
    var raw: UInt16 = raw_ptr[]
    var f32_bits: UInt32 = UInt32(raw) << 16
    var f32_val = UnsafePointer[UInt32](to=f32_bits).bitcast[Float32]()[]
    return Float64(f32_val)
```

#### Inject raw NaN bits for testing (bypass typed setter)

```mojo
fn make_bf16_nan_tensor(raw_bits: UInt16) -> ExTensor:
    var t = ExTensor(Shape(1), DType.bfloat16)
    t._data.bitcast[UInt16]()[0] = raw_bits
    return t
```

#### Three NaN invariant tests

```mojo
def test_bf16_nan_canonical_hash():
    var t1 = make_bf16_nan_tensor(0x7FC0)
    var t2 = make_bf16_nan_tensor(0x7FC0)
    assert_equal(hash(t1), hash(t2))

def test_bf16_nan_negative_hash():
    var t1 = make_bf16_nan_tensor(0xFFC0)
    var t2 = make_bf16_nan_tensor(0xFFC0)
    assert_equal(hash(t1), hash(t2))

def test_bf16_nan_cross_variant_hash():
    var t_pos = make_bf16_nan_tensor(0x7FC0)
    var t_neg = make_bf16_nan_tensor(0xFFC0)
    assert_equal(hash(t_pos), hash(t_neg))
```

BF16 NaN bit patterns reference:

| Pattern | Hex | Meaning |
| --------- | ----- | --------- |
| `0111 1111 1100 0000` | `0x7FC0` | Canonical positive quiet NaN |
| `1111 1111 1100 0000` | `0xFFC0` | Negative quiet NaN |
| `0111 1111 1000 0000` | `0x7F80` | Positive Infinity (NOT NaN — mantissa is zero) |

---

### Pattern 4 — BFloat16 Regression Tests (Silent No-Op)

Audit dtype-dispatched functions for missing bfloat16 branches:

```bash
grep -n "elif self._dtype == DType" shared/core/extensor.mojo | grep -A1 "float64"
```

Three-part regression pattern (use exactly-representable values: 0.5, 1.0, 1.5, 2.0, -1.0):

```mojo
# 1. Zero-guard: read path
fn test_get_fn_bfloat16() raises:
    var t = zeros([1], DType.bfloat16)
    t._set_float64(0, 1.5)          # seed via trusted float64 path
    var got = t._get_fn(0)
    assert_true(Float64(got) != 0.0, "bfloat16 _get_fn returned 0 — branch missing")
    assert_almost_equal(Float64(got), 1.5, tolerance=1e-2)

# 2. Zero-guard: write path
fn test_set_fn_bfloat16() raises:
    var t = zeros([1], DType.bfloat16)
    t._set_fn(0, FloatType(1.5))
    var got = t._get_float64(0)     # read via trusted float64 path
    assert_true(got != 0.0, "bfloat16 _set_fn silently wrote zero — branch missing")
    assert_almost_equal(got, 1.5, tolerance=1e-2)

# 3. Round-trip
fn test_get_fn_bfloat16_roundtrip() raises:
    var t = zeros([4], DType.bfloat16)
    t._set_fn(0, FloatType(1.0))
    t._set_fn(1, FloatType(2.0))
    t._set_fn(2, FloatType(0.5))
    t._set_fn(3, FloatType(-1.0))
    assert_almost_equal(Float64(t._get_fn(0)), 1.0, tolerance=1e-2)
    assert_almost_equal(Float64(t._get_fn(1)), 2.0, tolerance=1e-2)
    assert_almost_equal(Float64(t._get_fn(2)), 0.5, tolerance=1e-2)
    assert_almost_equal(Float64(t._get_fn(3)), -1.0, tolerance=1e-2)
```

Tolerance rationale:

| Dtype | Mantissa bits | Precision | Tolerance |
| ------- | ------------- | ---------- | --------- |
| bfloat16 | 7 | ~2 decimal digits | `1e-2` |
| float16 | 10 | ~3 decimal digits | `1e-3` |
| float32 | 23 | ~7 decimal digits | `1e-6` |

---

### Pattern 5 — UInt Bitwise NOT Tests

Create a standalone file `tests/shared/core/test_uint_bitwise_not.mojo` with 4 cases per type
(16 total):

```mojo
fn test_uint8_not_zero() raises:
    var result: UInt8 = ~UInt8(0)
    if result != 255:
        raise Error("~UInt8(0) expected 255, got " + String(result))

fn test_uint8_not_max() raises:
    var result: UInt8 = ~UInt8(255)
    if result != 0:
        raise Error("~UInt8(255) expected 0, got " + String(result))

fn test_uint8_not_alternating() raises:
    var result: UInt8 = ~UInt8(0b10101010)
    if result != 85:
        raise Error("~UInt8(0b10101010) expected 85, got " + String(result))

fn test_uint8_double_inversion() raises:
    var val: UInt8 = 42
    if ~~val != val:
        raise Error("~~UInt8(42) expected 42")
```

Alternating bit values per type:

| Type | Input | Expected |
| ------ | ------- | ---------- |
| UInt8 | `0b10101010` (170) | `0b01010101` (85) |
| UInt16 | `0xAAAA` (43690) | `0x5555` (21845) |
| UInt32 | `0xAAAAAAAA` (2863311530) | `0x55555555` (1431655765) |
| UInt64 | `0xAAAAAAAAAAAAAAAA` | `0x5555555555555555` |

Register in CI explicit file lists (if project uses them):

```yaml
pattern: "... test_unsigned.mojo test_uint_bitwise_not.mojo ..."
```

---

### Pattern 6 — UInt Overflow/Wrap-Around Tests

Extend the existing `test_unsigned.mojo` (do not create a new file). Three tests per type
(12 overflow + 3 sanity = 15 total):

```mojo
fn test_uint8_add_overflow() raises:
    var max_val: UInt8 = 255
    var one: UInt8 = 1
    var result = max_val + one
    if result != 0:
        raise Error("UInt8(255) + 1 should wrap to 0, got " + String(result))
```

Use typed variables, not literal expressions, to ensure arithmetic stays in the correct type.

Overflow-triggering values:

| Type | Add overflow | Sub underflow | Mul overflow (a, b) |
| ------ | ------------ | ------------- | ------------------- |
| UInt8 | `255 + 1` | `0 - 1` | `16 * 16 = 0` |
| UInt16 | `65535 + 1` | `0 - 1` | `256 * 256 = 0` |
| UInt32 | `4294967295 + 1` | `0 - 1` | `65536 * 65536 = 0` |
| UInt64 | `max + 1` | `0 - 1` | `4294967296 * 4294967296 = 0` |

---

### Pattern 7 — Value-Correctness Gap After as_contiguous

When an existing test only verifies `is_contiguous()` and `_strides` after `as_contiguous()`:

1. Confirm the tensor is built with `arange + reshape + transpose` (predictable values)
2. Derive expected values: for `(rows=3, cols=4)` transposed to `(4, 3)`, `c[j,i] = i*cols + j`
3. Append 12 `assert_almost_equal` calls (one per element) after the stride assertions

```mojo
# Verify element values are correctly reordered per transpose stride mapping.
# Original (3,4) row-major: a[i,j] = i*4 + j (values 0..11)
# After transpose to (4,3): t[j,i] = a[i,j]; row 0 = col 0 of original: 0, 4, 8
assert_almost_equal(c._get_float64(0), 0.0, 1e-6, "c[0,0] should be 0")
assert_almost_equal(c._get_float64(1), 4.0, 1e-6, "c[0,1] should be 4")
assert_almost_equal(c._get_float64(2), 8.0, 1e-6, "c[0,2] should be 8")
assert_almost_equal(c._get_float64(3), 1.0, 1e-6, "c[1,0] should be 1")
```

Assert values on the contiguous result `c`, not on the non-contiguous view `t`.

---

### Pattern 8 — View vs Copy Semantics

Two AnyTensor slice methods have different semantics:

| Method | Returns | `_is_view` | Use When |
| -------- | --------- | ------------ | ---------- |
| `tensor[a:b]` | Copy | `False` | Read-only slicing |
| `tensor.slice(a, b)` | View | `True` | Write-through to original |

```mojo
# WRONG: __getitem__ returns copy — writes don't affect original
var view = original[2:8]
view[0] = Float32(99.0)

# RIGHT: slice() returns view — writes affect original
var view = original.slice(2, 8)
view[0] = Float32(99.0)
```

When a function expects `AnyTensor` but you have `Tensor[dtype]`, add `.as_any()`.
Watch for cascading type changes when the return type of a function shifts.

---

### Pattern 9 — Unique `/tmp` Paths

```mojo
# Before
var test_path = "/tmp/test_remove_safely_3283.txt"

# After
from time import perf_counter_ns
var suffix = String(perf_counter_ns())
var test_path = "/tmp/test_remove_safely_" + suffix + ".txt"
```

`perf_counter_ns()` is the correct choice — Mojo v0.26.1 has no `uuid` module.
The inline import inside the function is valid Mojo syntax.

---

### Pattern 10 — Re-Enabling Disabled/Stubbed Tests

Before writing anything, determine the disable pattern:

| Pattern | Indicator | Action |
| --------- | ----------- | -------- |
| Stub file | `main()` only prints "SKIPPED" | Write all tests from scratch |
| NOTE-disabled | `NOTE: temporarily disabled pending X` | Check if X is resolved, then write tests |
| TODO commented-out | `# var b = fn(a)` + `pass  # Placeholder` | Uncomment + fix syntax |
| Backward-pass disabled | `# DISABLED — ownership issues` | Check type alias, write analytical tests |
| pytest.skip() | `if not file.exists(): pytest.skip(...)` | Fix path or config, remove guard |

Always `Read` the actual file before assuming its structure from the issue description.

Common Mojo syntax bugs in commented-out code:

| Bug Pattern | Fix |
| ------------- | ----- |
| `target_shape[0] = 4` | `target_shape.append(4)` |
| `var b = tile(a, 3)` | `var reps = List[Int](); reps.append(3); var b = tile(a, reps)` |
| `List[Int](1, 2, 3)` | Use list literals `[1, 2, 3]` (Mojo v0.26.1+) |

DataLoader requires 2D input — always use `[n_samples, feature_dim]`:

```mojo
var data = ones([n_samples, 10], DType.float32)
var labels = zeros([n_samples, 1], DType.float32)
return DataLoader(data^, labels^, batch_size=4)
```

Commit without mojo-format on GLIBC-old hosts:

```bash
SKIP=mojo-format git commit -m "fix(tests): re-enable X tests"
```

---

### Pattern 11 — Annotating Stale Placeholders

Every placeholder upgrade involves two issues: the dependency (#dep) and a
staleness-tracker (#tracker):

```mojo
# Before
fn test_from_array_1d() raises:
    """NOTE(#3013): placeholder."""
    pass

# After
fn test_from_array_1d() raises:
    """Blocked on #3013 (from_array() not yet implemented).
    Tracked by #4127 to prevent staleness.
    Once #3013 merges: [0.5, 1.0, 1.5] -> shape [3], dtype float32."""
    # TODO(#3013): implement when from_array() ships
    pass
```

Use `docs(tests):` commit prefix — no behavior changes.

---

### Pattern 12 — Resolving Blocked TODO Markers

```bash
# Phase A: verify blocker is closed
gh issue view <N> --json state -q '.state'   # must return "CLOSED"

# Phase B: locate all markers
grep -rn "TODO.*#<N>\|TODO(#<N>)" --include="*.mojo" .

# Phase C: check for implementation on a feature branch
git branch --all | grep "<N>"
git cherry-pick <commit-hash> --no-commit
```

After cherry-picking or implementing:
1. Remove `# TODO(#N)` lines
2. Uncomment test code
3. Replace `pass  # Placeholder` with real assertions
4. Verify no markers remain: `grep -rn "TODO.*#<N>" --include="*.mojo" .`

## Results & Parameters

### DType string formats

| Expression | Output |
| ----------- | ------- |
| `String(DType.float32)` | `"float32"` |
| `String(Float64(0.0))` | `"0.0"` |
| `String(DType.int32)` | `"int32"` |
| `String(DType.bool)` | `"bool"` |

### ExTensor str/repr expected outputs

```text
# float32
ExTensor([0.0, 1.0, 2.0], dtype=float32)

# int32 (no decimals)
ExTensor([0, 1, 2], dtype=int32)

# bool
ExTensor([False, True, False], dtype=bool)

# __repr__ float32
ExTensor(shape=[2, 2], dtype=float32, numel=4, data=[1.0, 1.0, 1.0, 1.0])

# __repr__ int32
ExTensor(shape=[3], dtype=int32, numel=3, data=[0, 1, 2])
```

### Bfloat16 safe test values

```text
Safe (power-of-2 fractions):    0.0, 0.5, 1.0, 1.5, 2.0, -0.5, -1.0, -1.5, -2.0
Unsafe (not exact in bfloat16): 0.1, 0.3, 1.3, 2.7, 3.9
```

### Local Mojo environment note

Mojo binary requires GLIBC 2.32+. On hosts with older GLIBC, tests only run in CI
(Docker). Pre-commit hooks still validate formatting locally. Use `SKIP=mojo-format`
for the mojo format hook when committing on those hosts.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Grep for `__str__` in extensor.mojo before implementing | Expected to find existing implementation based on issue description | Methods were absent — only found in unrelated `nvfp4.mojo` | Always verify implementation existence before activating tests; issue descriptions can be wrong |
| Run `pixi run mojo test` locally | Tried to verify tests on host | GLIBC version mismatch (2.31 vs required 2.32+) on most ProjectOdyssey dev machines | Mojo tests can only run in CI Docker; verify syntax via pre-commit hooks |
| Use `uuid` module for unique tmp path | `from uuid import uuid4` | No `uuid` module in Mojo v0.26.1 stdlib | Use `perf_counter_ns()` instead |
| Test 0xFF80 as negative BF16 NaN | Used 0xFF80 as "negative NaN" bit pattern | `0xFF80` is BF16 negative infinity (mantissa=0), not NaN | BF16 NaN requires exp=0xFF AND mantissa != 0; negative quiet NaN is `0xFFC0` |
| Numeric cast for BF16 in `_get_float64` | `Float64(Float32(BFloat16))` two-step cast | CPU numeric cast canonicalizes NaN bits, breaking hash consistency | Use raw bit manipulation: UInt16 read, shift left 16, Float32 bitcast |
| Use `_set_float64` to inject BF16 NaN | Called typed setter with NaN value | Same numeric cast path immediately canonicalizes the injected NaN | Use `bitcast[UInt16]` pointer to write raw bits directly |
| Assumed `__getitem__(Slice)` returns view | Asserted `_is_view == True` on `tensor[2:8]` | `__getitem__(Slice)` explicitly returns a copy (`_is_view = False`) | Read method docstring; use `tensor.slice(a, b)` for views |
| Fixed tuple destructuring without checking call sites | Changed `var (a,b,c) = fn()` to subscript access | Introduced new error: `forward(input)` failed because Tensor cannot convert to AnyTensor | When fixing one error, check ALL other calls in that function for type compatibility |
| `dtype.is_integral()` for integer dtype check | Called `.is_integral()` on dtype | Untested locally due to GLIBC mismatch; codebase never used this pattern | Use explicit `== DType.xxx` comparisons to match existing codebase style |
| Creating new file instead of extending | Created `test_uint_overflow.mojo` for overflow tests | File `test_unsigned.mojo` already had the right structure | Always check for existing test files before creating new ones; extend, don't duplicate |
| Assuming disabled tests existed but were gated | Expected skip guard or `@disabled` annotation | File had zero test functions — it was a complete stub | Always `Read` the actual file before assuming its structure from issue description |
| Using `List[Int](1, 2, 3)` constructor syntax | Older Mojo list construction pattern | Mojo v0.26.1+ uses list literals `[1, 2, 3]` | Compiler is truth — use list literal syntax |
| DataLoader with 1D data `[n_samples]` | Passed flat tensor to DataLoader | DataLoader reads `shape()[1]` for feature_dim, panics on 1D | DataLoader requires 2D input: `[n_samples, feature_dim]` |
| Using `_get_float64(i)` on non-contiguous tensor | Asserting values on `t` before `as_contiguous()` | `_get_float64(i)` reads flat memory index, ignoring strides | Assert values on `c` (the contiguous result), not on the non-contiguous view |
| Using bfloat16 round-trip with `2.7` | Copied float32 test value to bfloat16 | 2.7 is not exactly representable in bfloat16 | Use only power-of-2 fractions for bfloat16 tests |
| Cherry-pick waiting for blocking issue to be in main | Waited for #2722 to merge to main | Implementation was on branch `2722-auto-impl`, not yet in main | Check `git branch --all` and cherry-pick from feature branch when needed |
| Implement tests without checking if blocking issue merged | Assumed feature needed re-implementation | Code fix was already present in a prior commit (`3c1b07fa`) | Always check both the implementation AND the tests — a fixed function can still lack coverage |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issues #3162, #3376, #3293, #3292, #4060, #3910, #3842, PR #5097, #3013, #3077, #4127, #3082, #3081 | Absorbed from 12 member skills; see `.history` file |
