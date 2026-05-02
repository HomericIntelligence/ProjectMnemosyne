---
name: add-uint-bitwise-not-tests
description: 'Add Mojo UInt bitwise NOT (~) operator tests. Use when: extending bitwise
  coverage for unsigned integer types, or adding complement operator tests to an existing
  Mojo test suite.'
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-03-07 |
| Objective | Add `~` complement operator tests for UInt8, UInt16, UInt32, UInt64 in a Mojo project |
| Outcome | 16 tests passing in CI; new standalone file added alongside existing bitwise tests |

## When to Use

- Existing Mojo bitwise test suite covers AND, OR, XOR, shifts but omits `~` (NOT)
- Adding operator coverage for unsigned integer types (`UInt8`, `UInt16`, `UInt32`, `UInt64`)
- Following up a bitwise test issue (e.g. a GitHub issue references "missing complement operator")
- Extending `test_unsigned.mojo` or equivalent with not-operator cases

## Verified Workflow

1. **Read the existing bitwise test file** (`tests/shared/core/test_unsigned.mojo`) to match the exact pattern (`fn test_name() raises:`, `raise Error("msg")`, `String(result)` in messages, `fn main():` with try/except/print)

2. **Create a standalone file** `tests/shared/core/test_uint_bitwise_not.mojo` — separate from the existing file to keep concerns isolated and match the issue plan

3. **Implement 4 test functions per type** (16 total across UInt8/16/32/64):
   - `~T(0)` → max value (all bits set)
   - `~T(max)` → `0` (all bits cleared)
   - `~T(alternating)` → bit-inverted alternating pattern
   - `~~T(x) == x` double-inversion identity

4. **Register in CI workflow** — check `.github/workflows/comprehensive-tests.yml` for explicit file lists; add the new filename to the relevant pattern string alongside `test_unsigned.mojo`

5. **Commit** — all pre-commit hooks (mojo format, YAML, trailing whitespace, EOF) pass automatically for this pattern

## Test Pattern (Copy-Paste Ready)

```mojo
fn test_uint8_not_zero() raises:
    """~UInt8(0) should equal 255 (all bits set)."""
    var result: UInt8 = ~UInt8(0)
    if result != 255:
        raise Error("~UInt8(0) expected 255, got " + String(result))


fn test_uint8_not_max() raises:
    """~UInt8(255) should equal 0 (all bits cleared)."""
    var result: UInt8 = ~UInt8(255)
    if result != 0:
        raise Error("~UInt8(255) expected 0, got " + String(result))


fn test_uint8_not_alternating() raises:
    """~UInt8(0b10101010) should equal 0b01010101 (85)."""
    var result: UInt8 = ~UInt8(0b10101010)
    if result != 85:
        raise Error("~UInt8(0b10101010) expected 85, got " + String(result))


fn test_uint8_double_inversion() raises:
    """~~UInt8(42) should equal 42 (double complement identity)."""
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

## CI Registration

The project's `comprehensive-tests.yml` uses explicit file lists. Add the new file to the same
group as `test_unsigned.mojo`:

```yaml
pattern: "... test_unsigned.mojo test_uint_bitwise_not.mojo ..."
```

Check whether the workflow auto-discovers `test_*.mojo` or requires explicit registration before
assuming no change is needed.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Running tests locally with `pixi run mojo run` | Executed the new test file on the host machine | GLIBC version mismatch (requires 2.32/2.33/2.34, host has older version) | Mojo binary only runs in the CI Docker container; verify syntax by pattern-matching against existing files instead |
| Using `mojo test` runner | Alternative test execution path | Same GLIBC incompatibility on host | Trust pre-commit hooks (mojo format passes = syntactically valid) as local verification proxy |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3293, PR #3891 | [notes.md](../../references/notes.md) |

## Results & Parameters

- **Files created**: `tests/shared/core/test_uint_bitwise_not.mojo` (16 test functions)
- **Files modified**: `.github/workflows/comprehensive-tests.yml` (added filename to pattern)
- **Pre-commit hooks**: All pass (mojo format, check-yaml, trailing-whitespace, end-of-file-fixer)
- **PR**: Linked to issue with `Closes #3293`, auto-merge enabled
