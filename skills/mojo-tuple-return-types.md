---
name: mojo-tuple-return-types
description: 'Correct Mojo v0.26.1 syntax for multi-value returns from fn methods.
  Use when: writing helpers that return multiple computed values, seeing ''no matching
  function in initialization'' on tuple return types, or extracting shared logic that
  needs to return (start, end, step, size) style tuples.'
category: architecture
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Task** | Return multiple values from a Mojo `fn` method |
| **Mojo Version** | v0.26.1 |
| **Key Error** | `error: no matching function in initialization` on `-> (Int, Int, Int, Int):` |
| **Fix** | Use `-> Tuple[Int, Int, Int, Int]:` in signature; `return (v1, v2, v3, v4)` in body; `result[0]` for access |

## When to Use

- Extracting a shared helper that returns multiple normalized/computed values (e.g., `_normalize_slice_indices → (start, end, step, result_size)`)
- Any `fn` return type annotation using parenthesized tuple syntax `-> (T, T)` — this is invalid in Mojo v0.26.1
- Debugging `no matching function in initialization` errors on function return types
- Porting Python code that uses tuple unpacking for multiple returns

## Verified Workflow

### Quick Reference

```mojo
# ✅ CORRECT: Tuple[...] in return type, paren in return body, [N] to index
fn _normalize_slice_indices(
    self,
    start: Optional[Int],
    end: Optional[Int],
    step: Optional[Int],
    size: Int,
) -> Tuple[Int, Int, Int, Int]:
    # ... compute s, e, step_val, result_size ...
    return (s, e, step_val, result_size)

# Caller:
var norm = self._normalize_slice_indices(slice.start, slice.end, slice.step, size)
var start = norm[0]
var end   = norm[1]
var step  = norm[2]
var result_size = norm[3]
```

### Step 1 — Identify the duplicate logic

Look for two or more code blocks that perform the same normalization steps (defaults, negative-index resolution, clamping). This is the extraction target.

### Step 2 — Write the helper signature with correct return type

```mojo
fn my_helper(
    self,
    param1: Optional[Int],
    param2: Optional[Int],
    size: Int,
) -> Tuple[Int, Int, Int]:   # ← Tuple[...] NOT (Int, Int, Int)
    ...
    return (a, b, c)          # paren syntax works fine in the body
```

Key rules for Mojo v0.26.1:
- **Return type**: `-> Tuple[T1, T2, T3, T4]` (angle-bracket generic syntax)
- **Return statement**: `return (v1, v2, v3, v4)` (parentheses work)
- **Element access**: `result[0]`, `result[1]`, etc. (subscript, NOT `.get[0, T]()`)

### Step 3 — Pass Optional[Int] correctly from a Slice

When the caller holds a `Slice`, pass its fields directly:

```mojo
var norm = self._normalize_slice_indices(slice.start, slice.end, slice.step, size)
```

`slice.start`, `slice.end`, `slice.step` are already `Optional[Int]` — no wrapping needed.

For the multi-dimensional `*slices` overload where no step is used, pass an explicit None:

```mojo
var norm = self._normalize_slice_indices(s.start, s.end, Optional[Int](None), size)
```

### Step 4 — Destructure into named variables at the call site

```mojo
var start       = norm[0]
var end         = norm[1]
var step        = norm[2]
var result_size = norm[3]
```

### Step 5 — Validate with existing tests

Run the slicing regression suite to confirm no behavior change:

```bash
just test-group tests/shared/core "test_extensor_slicing*.mojo"
```

Then run the new helper unit tests:

```bash
just test-group tests/shared/core test_normalize_slice_indices.mojo
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `-> (Int, Int, Int, Int):` in return type | Used Python-style parenthesized tuple syntax in the `fn` return type annotation | Mojo v0.26.1 does not support `(T, T, T, T)` as a return type — compiler error: `no matching function in initialization` | Always use `Tuple[T, T, T, T]` in the `->` annotation |
| `Tuple[Int, Int, Int, Int](v1, v2, v3, v4)` in return body | Tried explicit constructor syntax in return | Works but is verbose; the shorter `return (v1, v2, v3, v4)` is idiomatic and compiles fine | Paren syntax is fine in the **body**; only the **type annotation** needs `Tuple[...]` |

## Results & Parameters

### Confirmed working pattern (Mojo v0.26.1)

```mojo
fn _normalize_slice_indices(
    self,
    start: Optional[Int],
    end: Optional[Int],
    step: Optional[Int],
    size: Int,
) -> Tuple[Int, Int, Int, Int]:
    """Normalize slice indices for a single dimension.

    Returns:
        Tuple of (normalized_start, normalized_end, step_val, result_size).
    """
    var step_val = step.or_else(1)
    var s: Int
    var e: Int
    if step_val < 0:
        s = start.or_else(size - 1)
        e = end.or_else(-size - 1)
    else:
        s = start.or_else(0)
        e = end.or_else(size)

    if s < 0:
        s = size + s
    if e < 0:
        e = size + e

    var result_size: Int
    if step_val < 0:
        var neg_step = -step_val
        s = max(0, min(s, size - 1))
        e = max(-1, min(e, size - 1))
        result_size = max(0, ceildiv(s - e, neg_step))
    else:
        s = max(0, min(s, size))
        e = max(0, min(e, size))
        result_size = max(0, ceildiv(e - s, step_val))

    return (s, e, step_val, result_size)
```

### Other confirmed-working `Tuple` return signatures from the codebase

```mojo
fn compute_axis_strides(...) -> Tuple[Int, Int, Int]          # reduction_utils.mojo
fn global_avgpool_output_shape(...) -> Tuple[Int, Int, Int, Int]  # shape.mojo
fn get_dtype_range(...) -> Tuple[Float64, Float64]             # fuzz_dtypes.mojo
```

All follow the same pattern: `Tuple[T, ...]` in the type, `(v, ...)` in the return.
