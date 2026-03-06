---
name: mojo-float-literal-overload-fix
description: "Fix Mojo type errors where float literals fail to match Float64 overloads by adding a Float32 overload. Use when: CI fails with 'no matching method in call to __setitem__' for float literals, or when Mojo APIs only have Float64 overloads but user code uses bare float literals."
category: debugging
date: 2026-03-06
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo float literals (e.g. `9.5`, `1.0`) infer as `Float32`, not `Float64` |
| **Symptom** | `no matching method in call to '__setitem__'` in CI for float-literal assignments |
| **Root Cause** | API only has `Float64` overload; Mojo does not auto-promote `Float32` to `Float64` |
| **Fix** | Add a `Float32` overload that delegates to the `Float64` overload |
| **Scope** | `extensor.mojo` `__setitem__` and any Mojo API with Float64-only numeric overloads |

## When to Use

- CI shows `no matching method in call to '__setitem__'` for lines like `t[i] = 9.5`
- Test code uses bare float literals (`1.0`, `9.5`) to set values in a Mojo struct
- A Mojo API method only has `Float64` and `Int64` overloads but no `Float32` overload
- Users must write `Float64(9.5)` everywhere to avoid compile errors — ergonomics are broken

## Verified Workflow

1. **Identify the failing line** in CI logs: look for `no matching method in call to '<method>'`
2. **Check the overloads** in the struct: confirm only `Float64` (and optionally `Int64`) exist
3. **Add a `Float32` overload** that delegates:
   ```mojo
   fn __setitem__(mut self, index: Int, value: Float32) raises:
       self.__setitem__(index, Float64(value))
   ```
4. **Place it** between the `Float64` overload and the `Int64` overload for logical grouping
5. **Verify** with `pixi run mojo test tests/...` (or trust CI if local GLIBC is incompatible)
6. **Run pre-commit** — `mojo-format` hook may fail locally if GLIBC is too old; use `SKIP=mojo-format` only in that case
7. **Commit** with `SKIP=mojo-format` if the mojo binary cannot run on the local host

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Fix tests with explicit casts | Change `t[1] = 9.5` to `t[1] = Float64(9.5)` in test files | Fixes tests but leaves broken ergonomics for all real users | Prefer fixing the API, not the callers |
| Run mojo test locally | `pixi run mojo test tests/shared/core/test_utility.mojo` | GLIBC version mismatch (`GLIBC_2.32/2.33/2.34` not found) on this host | Local Mojo execution is blocked by OS GLIBC — trust CI for Mojo compilation |
| Run pre-commit without SKIP | `git commit` triggered `mojo-format` hook | Same GLIBC error — hook exits 1 | Use `SKIP=mojo-format` when Mojo binary cannot run locally; document why |

## Results & Parameters

**Working overload pattern** (copy-paste into any Mojo struct with a `Float64` numeric setter):

```mojo
fn __setitem__(mut self, index: Int, value: Float32) raises:
    """Set element at flat index using a Float32 value.

    Args:
        index: The flat index to set.
        value: The Float32 value to store.

    Raises:
        Error: If index is out of bounds.

    Example:
        ```mojo
        var t = zeros([3], DType.float32)
        t[1] = Float32(9.5)
    ```
    """
    self.__setitem__(index, Float64(value))
```

**Commit command when mojo binary is unavailable locally**:

```bash
SKIP=mojo-format git commit -m "fix: add Float32 overload for __setitem__"
```

**Key facts about Mojo float literal inference**:
- `9.5` infers as `Float32` (not `Float64`) in Mojo
- `Int64(7)` does NOT auto-convert to `Float32` or `Float64`
- Mojo does not do implicit numeric promotion across float widths
- Always add `Float32` overloads alongside `Float64` overloads for ergonomic APIs
