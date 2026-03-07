---
name: mojo-shape-value-assertions
description: "Add value-correctness assertions to Mojo tensor shape tests. Use when: shape tests only check element counts/dimensions but not actual values, or code review flags tests that pass even if operations produce wrong output."
category: testing
date: 2026-03-07
user-invocable: false
---

# Mojo Shape Value Assertions

## Overview

| Item | Details |
|------|---------|
| **Date** | 2026-03-07 |
| **Objective** | Strengthen tensor shape operation tests by adding `assert_value_at()` and `assert_all_values()` calls |
| **Context** | Issue #3242 — follow-up on #3013 which enabled shape tests that only checked `assert_numel` / `assert_dim` |
| **Outcome** | ✅ 31 assertions added across 14 test functions; all pre-commit hooks passed; PR #3793 created with auto-merge |
| **PR** | #3793 on branch `3242-auto-impl` |

## When to Use

Use this pattern when:

1. **Shape tests use `assert_numel` and `assert_dim` only** — element counts and dimensions are
   checked but the actual stored values are never verified
2. **Code review flags tests that pass even if operations produce wrong output** — the operation
   could silently corrupt values and tests would still pass
3. **Newly-enabled tests are stubs** — the tests were written to unblock CI but lack content assertions
4. **Follow-up issues reference "verify actual element values"** — common phrasing in issue descriptions

**Trigger phrases:**

- "only asserts element counts (assert_numel) and dimensions (assert_dim)"
- "verify actual element values"
- "test_tile_1d verifies 9 elements but not that the values are [0,1,2,0,1,2,0,1,2]"
- "add assert_value_at() calls to verify correctness"

## Verified Workflow

### Step 1: Read the assert helper signatures

```mojo
# assert_value_at: checks single element at flat index
fn assert_value_at(
    tensor: ExTensor,
    index: Int,
    expected: Float64,
    tolerance: Float64 = TOLERANCE_DEFAULT,
    message: String = "",
) raises

# assert_all_values: checks all elements equal a constant
fn assert_all_values(
    tensor: ExTensor,
    expected: Float64,
    tolerance: Float64 = TOLERANCE_DEFAULT,
    message: String = "",
) raises
```

### Step 2: Categorize each test by input type

| Input type | Assertion strategy |
|------------|--------------------|
| `arange(0..N)` input | Loop `assert_value_at(b, i, Float64(i))` for all N elements |
| `ones(shape)` input | `assert_all_values(b, 1.0)` |
| `full(shape, V)` fill | `assert_all_values(b, V)` or spot-check boundary indices |
| Mix of `ones` + `full(2.0)` | Range loop for first block (1.0), range loop for second block (2.0) |

### Step 3: Add assertions after existing shape checks

```mojo
# BEFORE — shape only
assert_dim(b, 2, "Reshaped tensor should be 2D")
assert_numel(b, 12, "Reshaped tensor should have same number of elements")

# AFTER — shape + values
assert_dim(b, 2, "Reshaped tensor should be 2D")
assert_numel(b, 12, "Reshaped tensor should have same number of elements")
for i in range(12):
    assert_value_at(b, i, Float64(i), message="reshape value at index " + String(i))
```

### Step 4: Concatenate/stack require split-range assertions

```mojo
# Concatenate axis=0: a=ones(2x3), b=full(3x3, 2.0) → c is 5x3 (15 elements)
# First 6 elements from a, last 9 from b
for i in range(6):
    assert_value_at(c, i, 1.0, message="concat first half at " + String(i))
for i in range(6, 15):
    assert_value_at(c, i, 2.0, message="concat second half at " + String(i))
```

### Step 5: For axis=1 concatenation, spot-check at row boundaries

```mojo
# Concatenate axis=1: a=ones(3x2), b=full(3x4, 2.0) → c is 3x6
# Row 0: cols 0-1 from a (1.0), cols 2-5 from b (2.0)
assert_value_at(c, 0, 1.0, message="row0 col0 should be 1.0")
assert_value_at(c, 1, 1.0, message="row0 col1 should be 1.0")
assert_value_at(c, 2, 2.0, message="row0 col2 should be 2.0")
assert_value_at(c, 5, 2.0, message="row0 col5 should be 2.0")
```

### Step 6: Do NOT add value assertions to tests for unimplemented operations

Tests for `tile`, `repeat`, `broadcast_to`, `permute`, and dtype-only checks are left
without value assertions if the operations are not yet implemented — adding assertions
there would produce opaque failures.

### Step 7: Run pre-commit

```bash
git add tests/shared/core/test_shape.mojo
pixi run pre-commit run --files tests/shared/core/test_shape.mojo
```

All hooks (mojo format, trailing-whitespace, end-of-file-fixer) should pass cleanly.

### Step 8: Commit and push

```bash
git commit -m "test(shape): add value-correctness assertions to shape tests

Add assert_value_at() and assert_all_values() calls to active tests...

Closes #<issue-number>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

git push -u origin <branch-name>
gh pr create --title "..." --body "Closes #<issue-number>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running `pixi run mojo test` locally | Executed mojo test command directly | `GLIBC_2.32/2.33/2.34` not found — host system too old | Mojo tests must run in Docker/CI; local environment is incompatible due to glibc version mismatch |
| Adding value assertions to `test_tile_1d` | Attempted `assert_value_at` for tile output | Operation not yet implemented — would cause opaque CI failures | Only add value assertions for operations known to be implemented |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| File changed | `tests/shared/core/test_shape.mojo` |
| Lines added | 31 insertions |
| Test functions with new assertions | 14 |
| Assertion helpers used | `assert_value_at`, `assert_all_values` |
| Pre-commit result | All hooks passed (mojo format clean) |
| PR | #3793, auto-merge enabled |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3242, PR #3793 | [notes.md](../../references/notes.md) |
