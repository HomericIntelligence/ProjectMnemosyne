---
name: mojo-hash-stability-test
description: "Pattern for testing Mojo __hash__ determinism by hashing the same instance multiple times. Use when: verifying hash stability for edge-case tensors, confirming no side effects from repeated hash calls."
category: testing
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | mojo-hash-stability-test |
| **Category** | testing |
| **Trigger** | Writing hash tests for Mojo types, especially edge cases like 0-element tensors |
| **Outcome** | A determinism test that hashes one instance N times and asserts all results are equal |

## When to Use

- A prior test used two independent instances (`hash(a) == hash(b)`) and you want a stronger guarantee
- You need to confirm `__hash__` has no side effects (e.g., mutating internal state) for a given instance
- The type under test has edge-case shapes (empty, single-element) where hash behavior may be non-obvious
- Following up on issue comments requesting "hash the same tensor instance multiple times"

## Verified Workflow

### Quick Reference

```mojo
fn test_hash_stability_repeated_calls() raises:
    """Test that hashing the same instance repeatedly returns equal values."""
    var shape = List[Int]()
    var a = full(shape, 0.0, DType.float32)

    assert_equal_int(
        Int(hash(a)),
        Int(hash(a)),
        "hash of empty tensor must be stable across repeated calls",
    )
    assert_equal_int(
        Int(hash(a)),
        Int(hash(a)),
        "hash of empty tensor must be stable on third call",
    )
```

### Step 1 — Identify the existing hash test block

Find the `# Test __hash__` section in the relevant test file (e.g., `tests/shared/core/test_utility.mojo`).
Read the existing tests to understand which helper functions (`assert_equal_int`, `full`, `arange`) are available.

### Step 2 — Write the stability test

Create a new `fn test_hash_stability_repeated_calls() raises:` after the last existing hash test.

Key points:

- Use a **single variable** (`var a = ...`), not two separate instances
- Call `hash(a)` at least three times in paired assertions
- Use the same assertion helper used elsewhere in the file (`assert_equal_int`)
- Cast the `UInt` hash result to `Int` to match the helper signature
- Choose an edge-case shape (empty `List[Int]()` for a 0-element tensor)

### Step 3 — Register in main()

Add the function call immediately after the last existing hash test call in `main()`:

```mojo
    test_hash_same_values_different_dtype()
    test_hash_stability_repeated_calls()   # ← add here
```

### Step 4 — Verify

Run the specific test group locally or via CI:

```bash
just test-group "tests/shared/core" "test_utility.mojo"
# or
pixi run mojo test tests/shared/core/test_utility.mojo
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Two-instance comparison only | `hash(a) == hash(b)` with two separate instances | Passes even if hash has side effects that reset on each new instance | Single-instance repeated calls are a stronger stability guarantee |
| Asserting exact hash value | Hardcoding expected hash value in assertion | Hash seed or dtype ordinal may vary across builds/platforms | Assert equality between calls, not against a magic constant |

## Results & Parameters

- **Test file**: `tests/shared/core/test_utility.mojo`
- **Dtype used**: `DType.float32` (matches existing empty-tensor hash tests)
- **Shape**: empty `List[Int]()` → 0-element scalar tensor
- **Number of calls checked**: 3 (two `assert_equal_int` calls, each comparing consecutive `hash(a)` invocations)
- **Assert helper**: `assert_equal_int(Int(hash(a)), Int(hash(a)), "<message>")`
- **Registration location**: after `test_hash_same_values_different_dtype()` in `main()`
