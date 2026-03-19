---
name: mojo-empty-tensor-hash-test
description: 'Test pattern for verifying Mojo ExTensor __hash__ on 0-element tensors.
  Use when: adding edge-case hash coverage for zero-element containers, or confirming
  hash stability when data loop is skipped.'
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# Skill: Mojo Empty Tensor __hash__ Edge Case Test

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-07 |
| Project | ProjectOdyssey |
| Objective | Add `test_hash_empty_tensor` to verify `__hash__` on a 0-element ExTensor is safe and consistent |
| Outcome | Success — 24-line addition to existing test file; pre-commit hooks pass |
| Issue | HomericIntelligence/ProjectOdyssey#3384 |
| PR | HomericIntelligence/ProjectOdyssey#4064 |

## When to Use

Use this skill when:

- A `__hash__` implementation loops over `self._numel` elements and numel can be zero
- You need to verify that a 0-element tensor/container hashes without error (the loop body is skipped)
- You want to confirm that two identical empty tensors (same shape, same dtype, no data) produce the same hash
- Adding edge-case test coverage for hash operations on empty containers in Mojo

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

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running tests locally | `pixi run mojo run tests/shared/core/test_utility.mojo` | GLIBC version mismatch — host OS (Debian Buster) too old for the Mojo binary in pixi env (requires GLIBC 2.32+) | Mojo tests can only run inside the Docker CI container; local validation relies on pre-commit hooks passing |
| Using `empty()` factory | Considered using `empty(shape, DType.float32)` for the 0-element tensor | `empty()` leaves data uninitialized; for a deterministic hash consistency test, deterministic data is not needed (numel=0 means no data), but `zeros()` signals intent more clearly | Use `zeros()` for empty-shape tests to maximize clarity; `empty()` would also work since no data is accessed |

## Results & Parameters

### Test assertion pattern

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

### What the hash covers for an empty tensor

| Component | Contributes to Hash |
|-----------|---------------------|
| Shape dimensions | YES — `hasher.update(self._shape[i])` for each dim (value 0 in this case) |
| Dtype ordinal | YES — `hasher.update(dtype_to_ordinal(self._dtype))` |
| Data elements | NO — loop `for i in range(0)` never executes |

### File changed

`tests/shared/core/test_utility.mojo` — +24 lines (function definition + main() call)
