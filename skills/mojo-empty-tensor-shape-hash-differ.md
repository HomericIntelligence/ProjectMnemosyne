---
name: mojo-empty-tensor-shape-hash-differ
description: 'Test pattern for verifying that empty Mojo ExTensors with different
  shapes produce different hashes. Use when: adding hash coverage for multi-dimensional
  empty tensors, confirming shape dimensions feed into __hash__ when numel=0, or following
  up on empty-tensor hash equality tests.'
category: testing
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
# Skill: Mojo Empty Tensor Shape Hash Discrimination Test

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-15 |
| Project | ProjectOdyssey |
| Objective | Add `test_hash_empty_tensor_shapes_differ` to verify `__hash__` distinguishes empty tensors by shape |
| Outcome | Success — ~30-line addition to existing test file; all CI checks pass |
| Issue | HomericIntelligence/ProjectOdyssey#4067 |
| Follow-up from | HomericIntelligence/ProjectOdyssey#3384 (empty tensor hash equality) |

## When to Use

Use this skill when:

- A `__hash__` implementation encodes shape dimensions even when `numel=0`
- You need to verify that `[0]`, `[0,0]`, and `[0,1]` empty tensors are distinguishable by hash
- A follow-up issue requests adding "shapes differ" coverage after a "same-shape equality" test was added
- The existing hash tests cover non-empty tensors and 1D empty tensors but not multi-dimensional empty tensors

Do NOT use when:

- The `__hash__` implementation is known not to encode shape dimensions (would require an implementation fix first)
- Empty multi-dimensional shape discrimination is already tested in the same test file

## Root Cause Pattern

When `numel=0`, the `__hash__` data loop is skipped entirely:

```mojo
# Hash data
for i in range(self._numel):   # numel=0 → loop never executes
    var val = self._get_float64(i)
    var int_bits = UnsafePointer[Float64](to=val).bitcast[UInt64]()[]
    hasher.update(int_bits)
```

Shape dimensions are hashed separately:

```mojo
for i in range(len(self._shape)):
    hasher.update(self._shape[i])
```

Without a multi-dimensional test, the shape loop coverage for empty tensors only exercises
a single shape entry (`[0]`). This means regressions in multi-dimension shape hashing
could go undetected.

## Verified Workflow

### Step 1: Read existing hash tests

Locate the `# Test __hash__` section in `tests/shared/core/test_utility.mojo` and note the
last test function and the corresponding call in `main()`:

```bash
grep -n "test_hash" tests/shared/core/test_utility.mojo
```

### Step 2: Create three empty tensors with different shapes

Use `zeros()` to construct 0-element tensors. The `numel` will be 0 for any shape that
contains a `0` dimension:

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

### Step 3: Assert all pairs differ

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

### Step 4: Register in main()

Add the call after `test_hash_empty_tensor()` in the `# __hash__` block:

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

### Step 5: Commit and push

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
| `assert_not_equal` for hash comparison | Using `assert_not_equal(hash(t1), hash(t2), ...)` | Function does not exist in the test utility helpers for UInt type | Use `if hash(a) == hash(b): raise Error(...)` — consistent with the existing `test_hash_different_values_differ` pattern in the same file |
| Local test run | `just test-mojo` locally on Debian Buster | GLIBC 2.28 on host; Mojo binary requires GLIBC 2.32+ | Run tests only in Docker/CI; validate locally with pre-commit hooks only |
| Checking if production code needed changes | Reviewed `extensor.mojo:2840` `__hash__` implementation | No change needed — shape loop already handles all dimensions regardless of numel | Read the `__hash__` implementation before writing a test; confirms test-only change is sufficient |

## Results & Parameters

### Assertion pattern for "hashes must differ"

```mojo
if hash(a) == hash(b):
    raise Error("descriptive message about which shapes are expected to differ")
```

### What the hash covers for empty multi-dimensional tensors

| Shape | numel | Shape loop iterations | Data loop iterations | Hash unique? |
|-------|-------|-----------------------|----------------------|--------------|
| `[0]` | 0 | 1 (value=0) | 0 | Yes |
| `[0, 0]` | 0 | 2 (values=0, 0) | 0 | Yes — 2 iterations vs 1 |
| `[0, 1]` | 0 | 2 (values=0, 1) | 0 | Yes — second dim differs |

### File changed

`tests/shared/core/test_utility.mojo` — ~30 lines added (function definition + main() call)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #4067, PR implementing the test | [notes.md](../references/notes.md) |
