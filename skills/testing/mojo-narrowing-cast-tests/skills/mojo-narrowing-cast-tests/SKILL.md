---
name: mojo-narrowing-cast-tests
description: "Add narrowing conversion tests to Mojo test files documenting truncation semantics. Use when: a test file covers widening but not narrowing casts, or an issue asks to document truncation behavior of .cast[DType.uint8]() on UInt64 values > 255."
category: testing
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | mojo-narrowing-cast-tests |
| **Category** | testing |
| **Complexity** | Low |
| **Mojo runs locally** | No (GLIBC mismatch on host — Docker/CI only) |
| **Key pattern** | `if v.cast[DType.uint8]() != expected: raise Error(...)` |

This skill documents how to add narrowing conversion tests to an existing Mojo test file.
Narrowing casts (e.g. `UInt64 -> UInt8`) truncate to the low N bits, equivalent to
`value % 256` for uint8. Tests document this behavior at key boundary values.

## When to Use

- A Mojo test file covers widening conversions (UInt8 -> UInt16 -> UInt64) but not narrowing
- An issue asks to document `.cast[DType.uint8]()` truncation semantics on values > 255
- You need boundary value tests for integer narrowing casts
- A follow-up issue on an existing unsigned integer test file requests truncation documentation

## Verified Workflow

### 1. Read the existing test file

Identify the pattern used for assertions. In ProjectOdyssey the pattern is:

```mojo
if actual != expected:
    raise Error("description")
```

NOT `assert_equal` — the unsigned test files use raw `if/raise` style.

### 2. Identify the boundary values to test

For `UInt64 -> UInt8` (modulo 256):

| Input (UInt64) | `.cast[DType.uint8]()` | Expected | Rationale |
|----------------|------------------------|----------|-----------|
| 0 | -> uint8 | 0 | No-op passthrough |
| 255 | -> uint8 | 255 | Fits exactly, no truncation |
| 256 | -> uint8 | 0 | 256 mod 256 = 0 |
| 257 | -> uint8 | 1 | 257 mod 256 = 1 |
| 511 | -> uint8 | 255 | 511 mod 256 = 255 |
| 512 | -> uint8 | 0 | 512 mod 256 = 0 |

### 3. Add the test function before `main()`

```mojo
fn test_uint_narrowing_conversion() raises:
    """Test narrowing conversions that truncate via modulo 2^N semantics.

    When casting a UInt64 value > 255 to UInt8, the result is the low 8 bits
    of the original value, equivalent to value % 256.
    """
    # 256 % 256 = 0
    var v256: UInt64 = 256
    if v256.cast[DType.uint8]() != 0:
        raise Error("UInt64(256).cast[DType.uint8]() should be 0")

    # 257 % 256 = 1
    var v257: UInt64 = 257
    if v257.cast[DType.uint8]() != 1:
        raise Error("UInt64(257).cast[DType.uint8]() should be 1")

    # 511 % 256 = 255
    var v511: UInt64 = 511
    if v511.cast[DType.uint8]() != 255:
        raise Error("UInt64(511).cast[DType.uint8]() should be 255")

    # 512 % 256 = 0
    var v512: UInt64 = 512
    if v512.cast[DType.uint8]() != 0:
        raise Error("UInt64(512).cast[DType.uint8]() should be 0")

    # 255 fits exactly — no truncation
    var v255: UInt64 = 255
    if v255.cast[DType.uint8]() != 255:
        raise Error("UInt64(255).cast[DType.uint8]() should be 255")

    # 0 is a no-op
    var v0: UInt64 = 0
    if v0.cast[DType.uint8]() != 0:
        raise Error("UInt64(0).cast[DType.uint8]() should be 0")
```

### 4. Wire into `main()` after the widening conversion test

```mojo
    try:
        test_uint_narrowing_conversion()
        print("OK test_uint_narrowing_conversion")
    except e:
        print("FAIL test_uint_narrowing_conversion:", e)
```

### 5. Commit — pre-commit hooks pass without SKIP

Unlike some Mojo test work, this change is pure `.mojo` formatting that `mojo format`
handles cleanly. All pre-commit hooks pass without needing `SKIP=`:

```bash
git add tests/shared/core/test_unsigned.mojo
git commit -m "test(unsigned): add narrowing conversion tests (UInt64 -> UInt8 truncation)

Add test_uint_narrowing_conversion() to document the truncation semantics
of .cast[DType.uint8]() on UInt64 values > 255. Tests boundary values:
- 256 -> 0 (256 mod 256 = 0)
- 257 -> 1 (257 mod 256 = 1)
- 511 -> 255 (511 mod 256 = 255)
- 512 -> 0 (512 mod 256 = 0)
- 255 -> 255 (fits exactly, no truncation)
- 0 -> 0 (no-op)

Closes #<issue-number>"
```

### 6. Create PR with auto-merge

```bash
git push -u origin <branch>
gh pr create --title "test(unsigned): add narrowing conversion tests" \
  --body "Closes #<issue-number>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Run `pixi run mojo -I . tests/shared/core/test_unsigned.mojo` locally | Executed mojo on host | GLIBC_2.32/2.33/2.34 not found — Mojo requires newer libc | Mojo tests can only be verified in CI (Docker). Trust correct boundary math and submit to CI. |
| Use `assert_equal` from `testing` module | Considered importing `from testing import assert_equal` | The existing file uses raw `if/raise` pattern, not `assert_equal` | Match the existing test file's assertion style. Read the file before deciding on pattern. |

## Results & Parameters

### Truncation math for common narrowing casts

| Target | Modulus | Key boundary |
|--------|---------|-------------|
| uint8 | 256 | 256->0, 257->1, 511->255, 512->0 |
| uint16 | 65536 | 65536->0, 65537->1 |
| uint32 | 2^32 | 2^32->0, 2^32+1->1 |

### Complete function template

```mojo
fn test_uint_narrowing_conversion() raises:
    """Test narrowing conversions that truncate via modulo 2^N semantics."""
    var v256: UInt64 = 256
    if v256.cast[DType.uint8]() != 0:
        raise Error("UInt64(256).cast[DType.uint8]() should be 0")
    var v257: UInt64 = 257
    if v257.cast[DType.uint8]() != 1:
        raise Error("UInt64(257).cast[DType.uint8]() should be 1")
    var v511: UInt64 = 511
    if v511.cast[DType.uint8]() != 255:
        raise Error("UInt64(511).cast[DType.uint8]() should be 255")
    var v512: UInt64 = 512
    if v512.cast[DType.uint8]() != 0:
        raise Error("UInt64(512).cast[DType.uint8]() should be 0")
    var v255: UInt64 = 255
    if v255.cast[DType.uint8]() != 255:
        raise Error("UInt64(255).cast[DType.uint8]() should be 255")
    var v0: UInt64 = 0
    if v0.cast[DType.uint8]() != 0:
        raise Error("UInt64(0).cast[DType.uint8]() should be 0")
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #3672 (Issue #3179) | [notes.md](../references/notes.md) |
