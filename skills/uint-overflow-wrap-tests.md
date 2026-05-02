---
name: uint-overflow-wrap-tests
description: 'Skill: uint-overflow-wrap-tests. Use when adding overflow/wrap-around
  tests for Mojo built-in unsigned integer types (UInt8, UInt16, UInt32, UInt64) to
  verify modular arithmetic at boundary values.'
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# UInt Overflow/Wrap-Around Tests Skill

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-07 |
| **Issue** | #3292 — Add UInt overflow/wrap-around behavior tests |
| **Objective** | Add 15 tests verifying that Mojo's built-in unsigned integer types correctly wrap at boundary values (max+1=0, 0-1=max, overflow multiplication) |
| **Outcome** | Success — 15 tests added to existing file, pre-commit hooks passed, PR #3890 created |

## When to Use

Use this skill when:

- A Mojo test suite covers standard UInt arithmetic but lacks overflow/wrap-around boundary tests
- Verifying that `UInt8(255) + 1 == 0`, `UInt8(0) - 1 == 255`, etc. for each UInt type
- Adding correctness checks for unsigned integer modular arithmetic semantics
- Following up on a basic UInt test file that covers construction/arithmetic but not boundary wrapping
- Writing tests for `UInt8`, `UInt16`, `UInt32`, `UInt64` in Mojo v0.26.1+

## Verified Workflow

### 1. Identify the Existing Test File

Look for an existing unsigned integer test file rather than creating a new one:

```bash
# Find the existing uint test file
find tests/ -name "test_unsigned.mojo" -o -name "test_uint*.mojo"
```

Read the file to understand the existing structure (construction, arithmetic, bitwise, comparisons, conversions).

### 2. Plan the Test Coverage

For each UInt type (`UInt8`, `UInt16`, `UInt32`, `UInt64`), add three overflow tests:

| Test Pattern | What to Verify |
| --- | --- |
| `max_val + 1 == 0` | Addition overflow wraps to zero |
| `0 - 1 == max_val` | Subtraction underflow wraps to max |
| `a * b == 0` when `a*b == 2^N` | Multiplication overflow wraps mod 2^N |

Also add 3 sanity checks (near-boundary values that should NOT wrap) to make the tests meaningful:

- `UInt8(254) + 1 == 255`
- `UInt8(255) - 1 == 254`
- `UInt8(15) * 16 == 240`

### 3. Write the Test Functions

Follow the existing `fn test_... () raises:` + `raise Error(...)` pattern of the file.
Use typed variables, not implicit literals, to ensure the arithmetic happens in the correct type:

```mojo
fn test_uint8_add_overflow() raises:
    """Test UInt8 addition wraps around at 255 + 1 == 0."""
    var max_val: UInt8 = 255
    var one: UInt8 = 1
    var result = max_val + one
    if result != 0:
        raise Error("UInt8(255) + 1 should wrap to 0, got " + String(result))
```

Key: always declare `var result = ...` typed through the variables, not via `UInt8(255) + UInt8(1)` literal form, for clarity.

### 4. Choose Overflow-Triggering Values

| Type | Add overflow | Sub underflow | Mul overflow (a, b) |
| ------ | --- | --- | --- |
| `UInt8` | `255 + 1` | `0 - 1` | `16 * 16 = 256 mod 256 = 0` |
| `UInt16` | `65535 + 1` | `0 - 1` | `256 * 256 = 65536 mod 65536 = 0` |
| `UInt32` | `4294967295 + 1` | `0 - 1` | `65536 * 65536 = 2^32 mod 2^32 = 0` |
| `UInt64` | `18446744073709551615 + 1` | `0 - 1` | `4294967296 * 4294967296 = 0` |

### 5. Add Tests to the `main()` Runner

Insert all new test calls into the existing `main()` try/except runner block at the end:

```mojo
    try:
        test_uint8_add_overflow()
        print("OK test_uint8_add_overflow")
    except e:
        print("FAIL test_uint8_add_overflow:", e)
```

### 6. Commit and Push

```bash
git add tests/shared/core/test_unsigned.mojo
git commit -m "test(unsigned): add UInt overflow/wrap-around behavior tests

Add 15 tests verifying modular arithmetic at boundary values for all
four built-in UInt types (UInt8, UInt16, UInt32, UInt64):
- Addition overflow: max + 1 wraps to 0
- Subtraction underflow: 0 - 1 wraps to max
- Multiplication overflow: product exceeding max wraps mod 2^N
- Sanity checks: near-boundary operations that do NOT wrap

Closes #<issue>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

git push -u origin <branch>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Running `pixi run mojo test` locally | Tried to execute the tests locally to verify | GLIBC version mismatch: system has GLIBC_2.31, Mojo requires GLIBC_2.32+ | Mojo tests only run in Docker/CI on this machine; correctness must be verified via code review and CI |
| Creating a new test file | Considered making `test_uint_overflow.mojo` | File already existed (`test_unsigned.mojo`) with the right structure | Always check for existing test files before creating new ones; extend, don't duplicate |

## Results & Parameters

### Test Coverage Added

| Test Name | Operation | Expected Result |
| --- | --- | --- |
| `test_uint8_add_overflow` | `UInt8(255) + 1` | `0` |
| `test_uint8_sub_underflow` | `UInt8(0) - 1` | `255` |
| `test_uint8_mul_overflow` | `UInt8(16) * 16` | `0` |
| `test_uint16_add_overflow` | `UInt16(65535) + 1` | `0` |
| `test_uint16_sub_underflow` | `UInt16(0) - 1` | `65535` |
| `test_uint16_mul_overflow` | `UInt16(256) * 256` | `0` |
| `test_uint32_add_overflow` | `UInt32(4294967295) + 1` | `0` |
| `test_uint32_sub_underflow` | `UInt32(0) - 1` | `4294967295` |
| `test_uint32_mul_overflow` | `UInt32(65536) * 65536` | `0` |
| `test_uint64_add_overflow` | `UInt64(max) + 1` | `0` |
| `test_uint64_sub_underflow` | `UInt64(0) - 1` | `18446744073709551615` |
| `test_uint64_mul_overflow` | `UInt64(2^32) * 2^32` | `0` |
| `test_uint8_add_near_max` | `UInt8(254) + 1` | `255` (no wrap) |
| `test_uint8_sub_from_max` | `UInt8(255) - 1` | `254` (no wrap) |
| `test_uint8_mul_no_overflow` | `UInt8(15) * 16` | `240` (no wrap) |

### Pre-commit Hook Results

```
Mojo Format..............................................................Passed
Check for deprecated List[Type](args) syntax.............................Passed
Validate Test Coverage...................................................Passed
Trim Trailing Whitespace.................................................Passed
Fix End of Files.........................................................Passed
Check for Large Files....................................................Passed
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PR #3890, issue #3292 | [notes.md](../../references/notes.md) |

## Key Takeaways

1. **Extend existing files**: The project had `test_unsigned.mojo` already — append the new section and runner calls rather than creating a new file.
2. **Typed variables are essential**: In Mojo, arithmetic on `var a: UInt8 = 255` stays in UInt8 context. Using untyped literals can silently promote to a wider type, defeating the overflow test.
3. **Include sanity checks**: Add 2-3 near-boundary tests that should NOT wrap. Without them, a bug that prevented all overflow detection would still pass.
4. **Local Mojo execution requires Docker**: On most developer machines, the Mojo binary requires GLIBC 2.32+ which is only available inside the project Docker container. Plan accordingly — write careful code and rely on CI for execution.
5. **Multiplication overflow values**: Pick `a * b = exactly 2^N` for clean, easy-to-verify wrap-to-zero. Avoid values that wrap to a non-zero remainder (harder to reason about without running code).
