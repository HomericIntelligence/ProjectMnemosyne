---
name: mojo-setitem-glibc-hook-skip
description: 'Fix ExTensor missing __setitem__ and handle mojo format pre-commit failures
  from GLIBC mismatch. Use when: CI fails with ''expression must be mutable in assignment''
  on tensor subscript assignment, or mojo format hook fails locally with GLIBC_2.32+
  not found errors.'
category: ci-cd
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | ExTensor lacked `__setitem__`, causing `t[i] = v` to fail; mojo format pre-commit hook unusable locally due to GLIBC mismatch |
| **Project** | ProjectOdyssey |
| **PR** | #3385 (issue #3165) |
| **Files Changed** | `shared/core/extensor.mojo` |
| **Root Cause** | Missing `__setitem__` overloads + GLIBC 2.32/2.33/2.34 unavailable on dev host |

## When to Use

- CI "Core Utilities" fails with `error: expression must be mutable in assignment` at tensor subscript assignment lines
- Tests call `t[index] = value` but `ExTensor.__setitem__` does not exist
- Local `pixi run mojo format` exits with `GLIBC_2.32 not found` / `GLIBC_2.33 not found` / `GLIBC_2.34 not found`
- Pre-commit `mojo-format` hook fails with exit code 1 but no actual formatting errors (just GLIBC crash)
- Implementing `__setitem__` on a struct that already has `_set_float64` / `_set_int64` internal setters

## Verified Workflow

### Step 1: Diagnose the CI failure

```bash
gh run view <run-id> --log | grep -A5 "mutable\|setitem\|GLIBC"
```

Look for:
- `error: expression must be mutable in assignment` → missing `__setitem__`
- `GLIBC_2.3[234] not found` → local mojo format unusable

### Step 2: Find the insertion point and internal setter pattern

```bash
grep -n "__getitem__\|_set_float64\|_set_int64" shared/core/extensor.mojo
```

Key facts:
- `_set_float64(self, index: Int, value: Float64)` and `_set_int64(self, index: Int, value: Int64)` take plain `self` (mutate via raw pointer)
- `__setitem__` itself needs `mut self`
- Dispatch pattern: float dtypes (float16/32/64) → `_set_float64`; all others → `_set_int64`

### Step 3: Add `__setitem__` overloads after `__getitem__(self, index: Int)`

```mojo
fn __setitem__(mut self, index: Int, value: Float64) raises:
    """Set element at flat index."""
    if index < 0 or index >= self._numel:
        raise Error("Index out of bounds")

    if (
        self._dtype == DType.float16
        or self._dtype == DType.float32
        or self._dtype == DType.float64
    ):
        self._set_float64(index, value)
    else:
        self._set_int64(index, Int64(value))

fn __setitem__(mut self, index: Int, value: Int64) raises:
    """Set element at flat index using an integer value."""
    self.__setitem__(index, Float64(value))
```

### Step 4: Commit with SKIP=mojo-format

Since mojo requires GLIBC 2.32+ and the dev host doesn't have it, the local pre-commit hook always exits 1.
Per CLAUDE.md policy, `SKIP=hook-id` is valid for broken hooks — document the reason in the commit:

```bash
SKIP=mojo-format git commit -m "fix(core): add ExTensor __setitem__ overloads

SKIP=mojo-format: mojo binary requires GLIBC 2.32+ unavailable on this host.
CI Docker container will run mojo format in the correct environment.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

### Step 5: CI validates the format

The CI Docker image has the correct GLIBC version. The mojo format pre-commit hook
will run correctly there. If `test_utility.mojo` still triggers a formatter change,
check the CI pre-commit logs to see exactly which lines were reformatted, then apply
manually and commit again with `SKIP=mojo-format`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Run `pixi run mojo format` locally | Called mojo format on changed files | `GLIBC_2.32 not found` — mojo binary requires newer glibc than system provides | Mojo toolchain only works inside the project's Docker container on older Linux hosts |
| Find mojo in system PATH | `which mojo` and `find /usr /opt` | Only found the pixi env binary, same GLIBC issue | There is no alternative mojo installation; CI Docker is the only viable environment |
| Inspect formatter output manually | Compared test file against passing commits | Could not determine exact formatter changes without running it | Mojo formatter changes are subtle; the only reliable approach is to run it in CI |
| Use `--no-verify` | Considered bypassing hooks entirely | CLAUDE.md explicitly prohibits `--no-verify`; `SKIP=hook-id` is the correct alternative | Always use `SKIP=specific-hook-id` instead of blanket `--no-verify` |

## Results & Parameters

### Successful configuration

```bash
# Commit bypassing only the broken mojo-format hook
SKIP=mojo-format git commit -m "fix(core): ..."
# All other hooks (trailing-whitespace, end-of-file, check-yaml, etc.) still run
```

### ExTensor.__setitem__ dispatch table

| Dtype group | Internal setter called |
| ------------- | ---------------------- |
| `DType.float16`, `DType.float32`, `DType.float64` | `_set_float64(index, value)` |
| `DType.int8`, `DType.int16`, `DType.int32`, `DType.int64`, `DType.bool`, etc. | `_set_int64(index, Int64(value))` |

### Test assertions pattern (ProjectOdyssey)

```mojo
# Float64 overload
t[1] = 9.5
assert_value_at(t, 1, 9.5, 1e-6, "message")

# Int64 overload
t[2] = Int64(7)
assert_value_at(t, 2, 7.0, 1e-6, "message")

# Out-of-bounds raises
try:
    t[5] = 1.0
except:
    raised = True
```
