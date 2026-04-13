---
name: mojo-empty-tensor-hash-test
description: 'Test pattern for verifying Mojo ExTensor __hash__ on 0-element tensors.
  Use when: (1) adding edge-case hash coverage for zero-element containers, (2) confirming
  hash stability when data loop is skipped, (3) verifying that empty tensors with different
  shapes (e.g. [0], [0,0], [0,1]) produce distinct hashes, or (4) following up on
  empty-tensor hash equality tests with multi-dimensional shape discrimination coverage.'
category: testing
date: 2026-03-07
version: 2.0.0
user-invocable: false
---
# Skill: Mojo Empty Tensor __hash__ Edge Case Test

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-07 |
| Project | ProjectOdyssey |
| Objective | Add `test_hash_empty_tensor` and `test_hash_empty_tensor_shapes_differ` to verify `__hash__` on 0-element ExTensors is safe, consistent, and shape-discriminating |
| Outcome | Success — ~54 lines added across two test functions; all CI checks pass |
| Issue | HomericIntelligence/ProjectOdyssey#3384 |
| Follow-up Issue | HomericIntelligence/ProjectOdyssey#4067 |
| PR | HomericIntelligence/ProjectOdyssey#4064 |

## When to Use

Use this skill when:

- A `__hash__` implementation loops over `self._numel` elements and numel can be zero
- You need to verify that a 0-element tensor/container hashes without error (the loop body is skipped)
- You want to confirm that two identical empty tensors (same shape, same dtype, no data) produce the same hash
- Adding edge-case test coverage for hash operations on empty containers in Mojo
- A `__hash__` implementation encodes shape dimensions even when `numel=0`
- You need to verify that `[0]`, `[0,0]`, and `[0,1]` empty tensors are distinguishable by hash
- A follow-up issue requests adding "shapes differ" coverage after a "same-shape equality" test was added
- The existing hash tests cover non-empty tensors and 1D empty tensors but not multi-dimensional empty tensors

Do NOT use when:

- The `__hash__` implementation is known not to encode shape dimensions (would require an implementation fix first)
- Empty multi-dimensional shape discrimination is already tested in the same test file

## Root Cause Pattern

The `__hash__` method in ExTensor loops over data elements:

```mojo
# Hash data
for i in range(self._numel):   # numel=0 → loop never executes
    var val = self._get_float64(i)
    var int_bits = UnsafePointer[Float64](to=val).bitcast[UInt64]()[]
    hasher.update(int_bits)
```

For a tensor with shape `[0]`, `_numel=0` so the loop is skipped. The hash is determined
solely by the shape dimensions (one dimension of size 0) and the dtype ordinal. Without a
test, this edge case could regress silently if the hash logic changes.

## Verified Workflow

### Step 1: Identify the test file

Find the existing `__hash__` tests for the tensor type:

```bash
grep -r "__hash__" tests/ --include="*.mojo" -l
# → tests/shared/core/test_utility.mojo
```

### Step 2: Understand how to create a 0-element tensor

A tensor with shape `[0]` has `numel = 0`. Create it using existing factory functions:

```mojo
var shape = List[Int]()
shape.append(0)
var a = zeros(shape, DType.float32)  # _numel = 0
```

### Step 3: Write the test function

Add after the last existing `__hash__` test, before the next section:

```mojo
fn test_hash_empty_tensor() raises:
    """Test __hash__ for 0-element tensor hashes without error and consistently.

    A tensor with shape [0] has _numel=0, so the data loop is skipped.
    The hash is determined only by shape and dtype, but must still be stable.
    """
    var shape = List[Int]()
    shape.append(0)
    var a = zeros(shape, DType.float32)
    var b = zeros(shape, DType.float32)

    # Should not raise - the empty data loop must be safe
    var hash_a = hash(a)
    var hash_b = hash(b)

    # Two empty tensors with identical shape and dtype must hash the same
    assert_equal_int(
        Int(hash_a),
        Int(hash_b),
        "Empty tensors with same shape/dtype should have equal hashes",
    )
```

### Step 4: Register the test in main()

```mojo
# __hash__
print("  Testing __hash__...")
test_hash_immutable()
test_hash_different_values_differ()
test_hash_large_values()
test_hash_small_values_distinguish()
test_hash_empty_tensor()   # ← Add this line
```

### Step 5: Commit and push

```bash
git add tests/shared/core/test_utility.mojo
git commit -m "test(extensor): add test_hash_empty_tensor for 0-element tensor"
git push -u origin <branch>
```

Pre-commit hooks run automatically: `mojo format`, deprecated-list-check, trailing-whitespace, etc.

## Test 2: Shape Discrimination

### Step 1: Create three empty tensors with different shapes

Use `zeros()` to construct 0-element tensors. The `numel` will be 0 for any shape containing a `0` dimension:

```mojo
var shape_1d = List[Int]()
shape_1d.append(0)
var t1 = zeros(shape_1d, DType.float32)   # shape [0]

var shape_2d_00 = List[Int]()
shape_2d_00.append(0)
shape_2d_00.append(0)
var t2 = zeros(shape_2d_00, DType.float32)  # shape [0, 0]

var shape_2d_01 = List[Int]()
shape_2d_01.append(0)
shape_2d_01.append(1)
var t3 = zeros(shape_2d_01, DType.float32)  # shape [0, 1]
```

### Step 2: Write test_hash_empty_tensor_shapes_differ

Use the "must differ" assertion pattern (raise on collision, not `assert_not_equal`):

```mojo
fn test_hash_empty_tensor_shapes_differ() raises:
    """Test that empty tensors with different shapes produce different hashes."""
    var shape_1d = List[Int]()
    shape_1d.append(0)
    var t1 = zeros(shape_1d, DType.float32)

    var shape_2d_00 = List[Int]()
    shape_2d_00.append(0)
    shape_2d_00.append(0)
    var t2 = zeros(shape_2d_00, DType.float32)

    var shape_2d_01 = List[Int]()
    shape_2d_01.append(0)
    shape_2d_01.append(1)
    var t3 = zeros(shape_2d_01, DType.float32)

    if hash(t1) == hash(t2):
        raise Error(
            "Empty tensors [0] and [0,0] should have different hashes"
        )
    if hash(t1) == hash(t3):
        raise Error(
            "Empty tensors [0] and [0,1] should have different hashes"
        )
    if hash(t2) == hash(t3):
        raise Error(
            "Empty tensors [0,0] and [0,1] should have different hashes"
        )
```

### Step 3: Register in main() after test_hash_empty_tensor()

```mojo
    # __hash__
    print("  Testing __hash__...")
    test_hash_immutable()
    test_hash_different_values_differ()
    test_hash_large_values()
    test_hash_small_values_distinguish()
    test_hash_empty_tensor()
    test_hash_empty_tensor_shapes_differ()   # ← Add this
```

### Step 4: Commit and push

```bash
git add tests/shared/core/test_utility.mojo
git commit -m "test(utility): add test_hash_empty_tensor_shapes_differ"
git push -u origin <branch>
gh pr create --title "test(utility): verify empty tensors with different shapes hash differently" \
  --body "Closes #4067"
gh pr merge --auto --rebase <PR-number>
```

Pre-commit hooks run automatically: `mojo format`, trailing-whitespace, end-of-file-fixer.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running tests locally | `pixi run mojo run tests/shared/core/test_utility.mojo` | GLIBC version mismatch — host OS (Debian Buster) too old for the Mojo binary in pixi env (requires GLIBC 2.32+) | Mojo tests can only run inside the Docker CI container; local validation relies on pre-commit hooks passing |
| Using `empty()` factory | Considered using `empty(shape, DType.float32)` for the 0-element tensor | `empty()` leaves data uninitialized; for a deterministic hash consistency test, deterministic data is not needed (numel=0 means no data), but `zeros()` signals intent more clearly | Use `zeros()` for empty-shape tests to maximize clarity; `empty()` would also work since no data is accessed |
| `assert_not_equal` for hash comparison | Using `assert_not_equal(hash(t1), hash(t2), ...)` | Function does not exist in the test utility helpers for UInt type | Use `if hash(a) == hash(b): raise Error(...)` — consistent with the existing `test_hash_different_values_differ` pattern in the same file |
| Checking if production code needed changes | Reviewed `extensor.mojo:2840` `__hash__` implementation | No change needed — shape loop already handles all dimensions regardless of numel | Read the `__hash__` implementation before writing a test; confirms test-only change is sufficient |

## Results & Parameters

### Test assertion pattern (equality)

```mojo
# Verify no error + hash consistency for 0-element tensor
var hash_a = hash(a)
var hash_b = hash(b)
assert_equal_int(
    Int(hash_a),
    Int(hash_b),
    "Empty tensors with same shape/dtype should have equal hashes",
)
```

### Assertion pattern for "hashes must differ" (raise Error pattern)

```mojo
if hash(a) == hash(b):
    raise Error("descriptive message about which shapes are expected to differ")
```

### What the hash covers for an empty tensor

| Component | Contributes to Hash |
|-----------|---------------------|
| Shape dimensions | YES — `hasher.update(self._shape[i])` for each dim (value 0 in this case) |
| Dtype ordinal | YES — `hasher.update(dtype_to_ordinal(self._dtype))` |
| Data elements | NO — loop `for i in range(0)` never executes |

### Hash coverage for empty multi-dimensional tensors

| Shape | numel | Shape loop iterations | Data loop iterations | Hash unique? |
|-------|-------|-----------------------|----------------------|--------------|
| `[0]` | 0 | 1 (value=0) | 0 | Yes |
| `[0, 0]` | 0 | 2 (values=0, 0) | 0 | Yes — 2 iterations vs 1 |
| `[0, 1]` | 0 | 2 (values=0, 1) | 0 | Yes — second dim differs |

### Files changed

- `tests/shared/core/test_utility.mojo` — +24 lines for `test_hash_empty_tensor` (function definition + main() call)
- `tests/shared/core/test_utility.mojo` — ~30 lines added for `test_hash_empty_tensor_shapes_differ` (function definition + main() call)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3384, PR #4064 | Empty tensor hash equality test |
| ProjectOdyssey | Issue #4067 | Empty tensor shape hash discrimination test |
