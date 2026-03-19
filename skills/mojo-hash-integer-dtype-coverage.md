---
name: mojo-hash-integer-dtype-coverage
description: 'Add test coverage for __hash__ on integer-typed Mojo tensors where _get_float64
  casts int values to Float64 before hashing. Use when: adding hash tests for non-float
  dtypes, verifying integer tensor hash consistency, or closing coverage gaps on dtype-dispatched
  float64 conversion paths.'
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | mojo-hash-integer-dtype-coverage |
| **Category** | testing |
| **Effort** | Low — single function + main() call |
| **Risk** | None — additive test-only change |
| **PR Result** | #4059 merged cleanly |

## When to Use

- A `__hash__` implementation dispatches through a `_get_float64` helper that casts integer dtypes (int8, int16, int32, int64, uint*) to Float64 before hashing
- Existing hash tests only cover float32/float64 tensors, leaving integer branches untested
- A follow-up issue specifically requests a `test_hash_integer_dtype_consistent` test
- You want to confirm two independent tensors with the same integer values produce identical hashes

## Verified Workflow

1. **Read existing hash tests** to understand the naming pattern and assertion style.
   ```mojo
   # Existing pattern in test_utility.mojo
   fn test_hash_immutable() raises:
       var a = arange(0.0, 3.0, 1.0, DType.float32)
       var b = arange(0.0, 3.0, 1.0, DType.float32)
       assert_equal_int(Int(hash(a)), Int(hash(b)), "...")
   ```

2. **Add `test_hash_integer_dtype_consistent`** immediately after `test_hash_small_values_distinguish`:
   ```mojo
   fn test_hash_integer_dtype_consistent() raises:
       """Test __hash__ for integer-typed tensors produces consistent hashes.

       _get_float64 casts integer values to Float64 before hashing. Two separate
       tensors with identical integer values must produce the same hash.
       """
       var a = arange(0.0, 4.0, 1.0, DType.int32)
       var b = arange(0.0, 4.0, 1.0, DType.int32)

       var hash_a = hash(a)
       var hash_b = hash(b)
       assert_equal_int(
           Int(hash_a),
           Int(hash_b),
           "Integer-typed tensors with same values should have same hash",
       )
   ```

3. **Register in `main()`** under the `# __hash__` comment block:
   ```mojo
   test_hash_immutable()
   test_hash_different_values_differ()
   test_hash_large_values()
   test_hash_small_values_distinguish()
   test_hash_integer_dtype_consistent()   # <-- add this
   ```

4. **Run pre-commit** to verify Mojo format passes:
   ```bash
   pixi run pre-commit run --all-files
   ```

5. **Commit, push, create PR**:
   ```bash
   git add tests/shared/core/test_utility.mojo
   git commit -m "test(utility): add test_hash_integer_dtype_consistent for integer dtypes"
   git push -u origin <branch>
   gh pr create --title "..." --body "Closes #<issue>"
   gh pr merge --auto --rebase
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `DType.float32` for the integer test | Initial draft used float32 arange | Doesn't exercise the integer cast path that the issue targets | Use `DType.int32` explicitly to cover the `_get_float64` integer branch |
| Adding test after `main()` | Placed function after the `fn main()` block | Mojo sees it as dead code outside any callable | Always place helper test functions before `main()` |

## Results & Parameters

```mojo
# Exact function that passes CI
fn test_hash_integer_dtype_consistent() raises:
    var a = arange(0.0, 4.0, 1.0, DType.int32)
    var b = arange(0.0, 4.0, 1.0, DType.int32)
    var hash_a = hash(a)
    var hash_b = hash(b)
    assert_equal_int(
        Int(hash_a),
        Int(hash_b),
        "Integer-typed tensors with same values should have same hash",
    )
```

**Key observations:**
- `arange(start, end, step, DType.int32)` creates integer tensors via the float arange API; the dtype argument controls storage
- `hash()` returns `UInt64`; wrap with `Int()` for `assert_equal_int`
- The `_get_float64` cast path is implicit — no source changes needed, only a test
- All representable integers up to 2^53 survive the int→float64→hash round-trip without collision
