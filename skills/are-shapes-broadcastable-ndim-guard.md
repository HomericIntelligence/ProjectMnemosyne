---
name: are-shapes-broadcastable-ndim-guard
description: 'Documents the pattern of adding an ndim guard to broadcasting compatibility
  checks. Use when: a broadcastability helper silently returns True for (source, fewer-dim
  target) pairs due to a vacuous loop, or when protecting callers that rely on the
  helper directly.'
category: architecture
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | `are_shapes_broadcastable(shape1, shape2)` returned `True` when `shape2` had fewer dimensions than `shape1` because the right-to-left loop was vacuous — no iterations fired to return `False` |
| **Fix pattern** | Add `if len(shape2) < len(shape1): return False` as the first check, before the loop |
| **Why helper, not caller** | The guard belongs in the helper so all callers are protected, not just the one that discovered the bug |
| **Companion** | `broadcast_to` already had an explicit `raise Error` for the same case — add a comment noting both guards exist for different UX reasons |

## When to Use

- A broadcastability / compatibility helper returns `True` for `(non-empty source, fewer-dim target)` pairs
- The bug is caused by a vacuous loop (empty range means no `return False` fires)
- Multiple callers rely on the helper and any one of them could silently get a wrong answer
- You want the function signature / docstring to self-document the no-dimension-reduction rule

## Verified Workflow

### Quick Reference

```mojo
fn are_shapes_broadcastable(shape1: List[Int], shape2: List[Int]) -> Bool:
    var ndim1 = len(shape1)
    var ndim2 = len(shape2)

    # Broadcasting cannot reduce the number of dimensions
    if ndim2 < ndim1:
        return False

    var max_ndim = max(ndim1, ndim2)
    # ... rest of dimension-alignment loop unchanged ...
```

### Step 1 — Identify the vacuous-loop bug

Confirm the function body consists of a `for i in range(max_ndim)` loop that can exit cleanly with `return True` even when `ndim2 < ndim1`. The range is non-empty only when `max_ndim > 0` and the right-to-left indexing never produces a failing pair.

### Step 2 — Add the early-return guard

Insert `if ndim2 < ndim1: return False` as the **first** check in the function, before any other logic. Do not touch the loop body.

### Step 3 — Update the docstring

- Document the new invariant in the Returns section: "Broadcasting cannot reduce the number of dimensions: if shape2 has fewer dimensions than shape1, this function returns False immediately."
- Fix any docstring examples that showed the buggy behavior (e.g. `[3,4,5] vs [4,5] -> True` → `-> False`)
- Add a correct expanding-dims example: `[4,5] vs [3,4,5] -> True`

### Step 4 — Add a companion comment to callers with duplicate guards

If an existing caller (e.g. `broadcast_to`) already has its own guard that raises a descriptive `Error`, add a comment there noting both guards exist:

```mojo
# Cannot reduce number of dimensions (target must have >= dims than source).
# Note: are_shapes_broadcastable also enforces this guard, but we raise a
# descriptive Error here for better caller UX.
if len(target_shape) < len(shape):
    raise Error("broadcast_to: cannot broadcast to fewer dimensions")
```

### Step 5 — Write a dedicated test file

Keep the per-file test count reasonable (≤10 test functions per file). Create `test_<module>_part<N>.mojo` covering:

| Test | Expected |
| ------ | ---------- |
| `ndim_reduction_3d_to_2d` | `False` |
| `ndim_reduction_2d_to_1d` | `False` |
| `empty_target_nonempty_source` | `False` |
| `expanding_ndim_2d_to_3d` | `True` |
| `same_ndim_identical` | `True` |
| `broadcast_dim1` | `True` |
| `incompatible_dims_same_ndim` | `False` |
| `both_empty_scalar` | `True` |
| `scalar_source_to_1d` | `True` |

### Step 6 — Verify no regressions in callers

Because `broadcast_to` already guarded against the same case with an explicit error, the new guard in the helper is redundant but harmless for that caller. The value is for any other caller that called the helper directly without its own guard.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Fix only in `broadcast_to` | The original bug fix (issue #3279) added the guard only to `broadcast_to`, not to `are_shapes_broadcastable` | Other callers of `are_shapes_broadcastable` could still get a silently wrong `True` | Guards belong in the helper, not only in one caller |
| No docstring update | Leaving the old example `[3,4,5] vs [4,5] -> True` in the docstring | The docstring would continue to document the buggy behavior, misleading future readers | Always update docstring examples when fixing a bug in a helper |

## Results & Parameters

**Mojo version**: 0.26.1
**File changed**: `shared/core/broadcasting.mojo`
**Lines added**: 5 (guard + blank line + comment)
**Test file**: `tests/shared/core/test_broadcasting_part5.mojo` (9 tests, 0 failures)
**PR**: #4816 — merged via auto-merge rebase

**Minimal diff**:

```mojo
 fn are_shapes_broadcastable(shape1: List[Int], shape2: List[Int]) -> Bool:
     var ndim1 = len(shape1)
     var ndim2 = len(shape2)
+
+    # Broadcasting cannot reduce the number of dimensions
+    if ndim2 < ndim1:
+        return False
+
     var max_ndim = max(ndim1, ndim2)
```
