---
name: mojo-narrowing-cast-tests
description: "Documents how to add narrowing conversion tests in Mojo following the if/raise pattern. Use when: (1) adding UInt narrowing tests for a new target type, (2) extending test_unsigned.mojo with new cast coverage."
category: testing
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Pattern** | `if/raise` narrowing cast tests |
| **File** | `tests/shared/core/test_unsigned.mojo` |
| **Trigger** | New UInt narrowing path needs test coverage |
| **Mojo version** | 0.26.1 |
| **Mojo runs locally** | No (GLIBC mismatch on host — Docker/CI only) |

This skill documents how to add narrowing conversion tests to an existing Mojo test file.
Narrowing casts (e.g. `UInt64 -> UInt8`, `UInt64 -> UInt16`, `UInt64 -> UInt32`) truncate
to the low N bits, equivalent to `value % M` where M = 2^N. Tests document this behavior
at key boundary values.

## When to Use

- Adding a new `test_uint_narrowing_to_uintN()` function for a target type not yet covered
- Extending `test_unsigned.mojo` with additional cast coverage following issue follow-ups
- Verifying modular arithmetic (truncation) semantics for unsigned integer narrowing casts
- A Mojo test file covers widening conversions but not narrowing
- An issue asks to document `.cast[DType.uintN]()` truncation semantics

## Boundary Values Quick Reference

| Target | Modulus (M) | Boundary value | Expected result | Rationale |
|--------|-------------|----------------|-----------------|-----------|
| UInt8  | 256         | 256            | 0               | M % M = 0 |
| UInt8  | 256         | 257            | 1               | (M+1) % M = 1 |
| UInt8  | 256         | 255            | 255             | M-1 fits exactly |
| UInt16 | 65536       | 65536          | 0               | M % M = 0 |
| UInt16 | 65536       | 65537          | 1               | (M+1) % M = 1 |
| UInt16 | 65536       | 65535          | 65535           | M-1 fits exactly |
| UInt32 | 4294967296  | 4294967296     | 0               | M % M = 0 |
| UInt32 | 4294967296  | 4294967297     | 1               | (M+1) % M = 1 |
| UInt32 | 4294967296  | 4294967295     | 4294967295      | M-1 fits exactly |

## Verified Workflow

### 1. Read the existing test file

Identify the pattern used for assertions. In ProjectOdyssey the pattern is:

```mojo
if actual != expected:
    raise Error("description")
```

NOT `assert_equal` — the unsigned test files use raw `if/raise` style.

### 2. Find the insertion point

Grep for the most recently added narrowing test function to find where to insert the next:

```bash
grep -n "test_uint_narrowing" tests/shared/core/test_unsigned.mojo
```

Insert new functions immediately after the last existing narrowing function.

### 3. Write the new function using this template

```mojo
fn test_uint_narrowing_to_uintN() raises:
    """Test narrowing conversions from UInt64 to UIntN via modulo M semantics.

    When casting a UInt64 value > (M-1) to UIntN, the result is the low N bits
    of the original value, equivalent to value % M.
    """
    # M % M = 0
    var vM: UInt64 = M
    if vM.cast[DType.uintN]() != 0:
        raise Error("UInt64(M).cast[DType.uintN]() should be 0")

    # (M+1) % M = 1
    var vM1: UInt64 = M + 1
    if vM1.cast[DType.uintN]() != 1:
        raise Error("UInt64(M+1).cast[DType.uintN]() should be 1")

    # (M-1) fits exactly — no truncation
    var vMax: UInt64 = M - 1
    if vMax.cast[DType.uintN]() != (M - 1):
        raise Error("UInt64(M-1).cast[DType.uintN]() should be M-1")

    # 0 is a no-op
    var v0_N: UInt64 = 0
    if v0_N.cast[DType.uintN]() != 0:
        raise Error("UInt64(0).cast[DType.uintN]() should be 0")
```

### 4. Avoid variable name collisions

Use `v0_16`, `v0_32` (not `v0`) to avoid potential confusion with variables in nearby
functions, even though they're different scopes. Match the naming style of existing
functions (e.g., `v65536`, `v65537` for UInt16 boundaries).

### 5. Wire into `main()` after the previous narrowing test block

```mojo
    try:
        test_uint_narrowing_to_uintN()
        print("OK test_uint_narrowing_to_uintN")
    except e:
        print("FAIL test_uint_narrowing_to_uintN:", e)
```

### 6. Verify with pre-commit hooks

```bash
just pre-commit
```

Note: `just precommit` (no hyphen) does NOT exist. Always use `just pre-commit`.

### 7. Create PR with auto-merge

```bash
git push -u origin <branch>
gh pr create --title "test(unsigned): add UIntN narrowing conversion tests" \
  --body "Closes #<issue-number>" \
  --label "testing"
gh pr merge --auto --rebase <PR-number>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Run mojo locally | `pixi run mojo -I . tests/shared/core/test_unsigned.mojo` | GLIBC_2.32/2.33/2.34 not found — Mojo requires newer libc | Use CI (Docker) for test verification, not local host |
| Use `assert_equal` | Considered `from testing import assert_equal` | The existing file uses raw `if/raise` pattern | Match the existing test file's assertion style |
| Wrong just recipe | Ran `just precommit` | Recipe doesn't exist; correct name is `just pre-commit` | Check `just --list` if a recipe name is uncertain |
| Skill tool for commit | Tried `/commit-commands:commit` via Skill tool | Denied in don't-ask permission mode | Fall back to raw git/gh commands when Skill tool is denied |

## Results & Parameters

### Commit format

```bash
git commit -m "test(unsigned): add UInt16 and UInt32 narrowing conversion tests"
```

### PR creation

```bash
gh pr create \
  --title "test(unsigned): add UInt16 and UInt32 narrowing conversion tests" \
  --body "Closes #N" \
  --label "testing"
gh pr merge --auto --rebase <PR-number>
```

## Verified On

| Project | Issue | PR | Target types | Details |
|---------|-------|----|--------------|---------|
| ProjectOdyssey | #3179 | #3672 | UInt8 | [notes.md v1](../references/notes.md) |
| ProjectOdyssey | #3675 | #4765 | UInt16, UInt32 | [notes.md v2](../references/notes-3675.md) |
