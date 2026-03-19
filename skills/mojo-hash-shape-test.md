---
name: mojo-hash-shape-test
description: 'Add a Mojo test verifying tensors with identical data but different
  shapes produce different hashes. Use when: hash test suite lacks shape-sensitivity
  coverage, adding __hash__ edge-case tests to ExTensor, or following up on shape
  collision issues.'
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# Skill: Mojo Hash Shape-Sensitivity Test

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-07 |
| **Category** | testing |
| **Objective** | Add `test_hash_different_shapes_differ` to verify shape is encoded in `__hash__` |
| **Outcome** | Successfully added test; all pre-commit hooks passed on first attempt |
| **Context** | Issue #3380 - follow-up from #3164; `test_utility.mojo` lacked shape-collision edge case |

## When to Use

Use this skill when:

- A hash test suite covers equal-tensor and different-value cases but **not** shape differences
- You need to verify `__hash__` encodes shape information (not just element values)
- A follow-up issue requests adding the `[N]` vs `[1, N]` same-data different-shape test case
- Adding edge-case hash coverage for `ExTensor` or similar tensor types

Do NOT use when:

- The `__hash__` implementation is known not to encode shape (would require implementation fix first)
- Shape-sensitivity is already tested elsewhere in the same test file

## Verified Workflow

### Step 1: Identify the hash test section

Locate the `# Test __hash__` section in the target test file:

```bash
grep -n "__hash__" tests/shared/core/test_utility.mojo
```

### Step 2: Add the test function

Insert after the last existing hash test (e.g., `test_hash_small_values_distinguish`):

```mojo
fn test_hash_different_shapes_differ() raises:
    """Test that tensors with same data but different shapes produce different hashes."""
    # Create [3] tensor with values [1, 2, 3]
    var t1 = arange(1.0, 4.0, 1.0, DType.float32)

    # Create [1, 3] tensor with values [1, 2, 3]
    var shape = List[Int]()
    shape.append(1)
    shape.append(3)
    var t2 = arange(1.0, 4.0, 1.0, DType.float32)
    t2 = t2.reshape(shape)

    var hash_1 = hash(t1)
    var hash_2 = hash(t2)
    if hash_1 == hash_2:
        raise Error(
            "Tensors with same data but different shapes should have different hashes"
        )
```

### Step 3: Register in main()

Add the call inside the `# __hash__` block in `main()`:

```mojo
    # __hash__
    print("  Testing __hash__...")
    test_hash_immutable()
    test_hash_different_values_differ()
    test_hash_large_values()
    test_hash_small_values_distinguish()
    test_hash_different_shapes_differ()   # <-- add this
```

### Step 4: Commit and push

```bash
git add tests/shared/core/test_utility.mojo
git commit -m "test(utility): add hash test for same-data different-shape tensors"
git push -u origin <branch>
gh pr create --title "..." --body "Closes #NNNN"
gh pr merge --auto --rebase <PR-number>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | First attempt succeeded | — | Following existing `arange` + `reshape` pattern directly was sufficient |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Test name | `test_hash_different_shapes_differ` |
| Tensor shapes tested | `[3]` vs `[1, 3]` |
| Data | `arange(1.0, 4.0, 1.0, DType.float32)` → values `[1, 2, 3]` |
| Reshape method | `t2 = t2.reshape(shape)` with `shape = [1, 3]` |
| Pre-commit hooks | All passed (mojo format, trailing whitespace, test count badge) |
| Mojo test runner | Not runnable locally (GLIBC version mismatch) — CI validates |
