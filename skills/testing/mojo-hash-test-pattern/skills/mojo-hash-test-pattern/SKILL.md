---
name: mojo-hash-test-pattern
description: "Skill: mojo-hash-test-pattern. Use when: adding tests to verify that __hash__ on a Mojo tensor type differentiates by dtype even when logical values are identical, or confirming that dtype_to_ordinal is included in hash computation."
category: testing
date: 2026-03-07
user-invocable: false
---

# Mojo Hash Dtype-Differentiation Test Pattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Issue** | #3381 — Add `test_hash_different_dtypes_differ` for ExTensor |
| **Objective** | Add a test verifying that float32 and float64 tensors with identical logical values produce different hash values |
| **Outcome** | Success — one test function added, `main()` updated, PR #4057 created with auto-merge enabled |

## When to Use

Use this skill when:

- Adding a test to verify that `__hash__` distinguishes tensors of different dtypes (e.g., `float32` vs `float64`)
- Confirming that the hash implementation includes `dtype_to_ordinal` so dtype is part of the hash seed
- Following TDD for a hash method on a Mojo tensor/array struct
- The test file already has other hash tests (e.g., `test_hash_same_shape_same_values_equal`,
  `test_hash_small_values_distinguish`) and you need to extend the suite

## Verified Workflow

### 1. Confirm `dtype_to_ordinal` is included in `__hash__`

Before writing the test, verify the implementation includes dtype in the hash:

```bash
grep -n "dtype_to_ordinal\|__hash__" <package>/extensor.mojo
```

A correct implementation will include a line such as:

```mojo
hash_value = hash_value ^ dtype_to_ordinal(self.dtype())
```

This guarantees that two tensors with the same values but different dtypes will have different hashes.

### 2. Write the test function

Insert after the last existing hash test (e.g., `test_hash_small_values_distinguish`):

```mojo
fn test_hash_different_dtypes_differ() raises:
    """Test that tensors with same values but different dtypes hash differently."""
    var shape = List[Int]()
    shape.append(2)
    shape.append(2)
    var t_f32 = full(shape, Float64(1.0), DType.float32)
    var t_f64 = full(shape, Float64(1.0), DType.float64)
    if hash(t_f32) == hash(t_f64):
        raise Error(
            "float32 and float64 tensors with identical values should hash differently"
        )
```

Key points:

- Use `full(shape, Float64(value), DType.<dtype>)` — same helper already used by other hash tests
- Use `if hash(...) == hash(...): raise Error(...)` — matches the existing assertion style in the file
- The test name must be descriptive: `test_hash_different_dtypes_differ`
- No tolerance is needed — this is an equality check on integer hash values

### 3. Register the test in `main()`

Add the call immediately after `test_hash_small_values_distinguish()` inside the `# __hash__` block:

```mojo
    test_hash_small_values_distinguish()
    test_hash_different_dtypes_differ()
```

Do not add a new section header — this test belongs in the existing `# __hash__` block.

### 4. Verify pre-commit passes

Stage the modified test file and run pre-commit:

```bash
git add <test-path>/test_utility.mojo
git commit -m "test(utility): add test_hash_different_dtypes_differ for ExTensor"
```

The pre-commit suite includes `mojo format` (auto-formats the file) and a test-count badge
validator. Both must pass before the commit succeeds.

### 5. Push and create PR

```bash
git push -u origin <branch>
gh pr create --title "test(utility): add test_hash_different_dtypes_differ for ExTensor" \
  --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| None | Implementation was straightforward following existing hash test patterns | N/A | Reading existing hash tests first (same-shape, small-values) reveals the exact helper and assertion style to use |

## Results & Parameters

### Test Function Added

| Test | DType A | DType B | Value | Shape | Assertion |
|------|---------|---------|-------|-------|-----------|
| `test_hash_different_dtypes_differ` | `float32` | `float64` | `1.0` | `[2, 2]` | `hash(a) != hash(b)` |

### Key Parameters

- Tensor shape: `[2, 2]` (matches existing hash tests, avoids degenerate scalar edge cases)
- Logical value: `Float64(1.0)` (exact and non-zero; non-zero avoids zero-hash edge cases)
- Assertion: `if hash(t_f32) == hash(t_f64): raise Error(...)` (matches file's existing style)
- No tolerance required — hash values are integers

### Implementation Detail

The `__hash__` method in `ExTensor` includes:

```mojo
hash_value = hash_value ^ dtype_to_ordinal(self.dtype())
```

`dtype_to_ordinal` maps each `DType` to a unique integer, so XOR-ing it into the hash seed
guarantees that two tensors differing only in dtype produce different hashes, regardless of
their values or shape.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3381, PR #4057 | [notes.md](../references/notes.md) |
