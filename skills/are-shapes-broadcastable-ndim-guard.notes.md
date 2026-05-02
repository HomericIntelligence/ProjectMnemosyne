# Session Notes — are-shapes-broadcastable-ndim-guard

## Issue

GitHub issue #3859 — "Add are_shapes_broadcastable guard for 0-d target directly"

Follow-up from #3279, which fixed the vacuous-loop bug in `broadcast_to` but left
`are_shapes_broadcastable` itself silently returning `True` for `(non-empty source,
fewer-dim target)` pairs.

## Root Cause

`are_shapes_broadcastable` iterates `for i in range(max_ndim)` from right to left.
When `shape2` has fewer dims than `shape1`, `max_ndim = len(shape1)` but all
right-to-left index checks align correctly for the existing dims — the loop never
fires a `False`. The function exits the loop and hits `return True`.

Example:
- `shape1 = [3, 4, 5]` (ndim=3)
- `shape2 = [4, 5]` (ndim=2)
- Loop fires for i=0 (5==5 OK), i=1 (4==4 OK), i=2 (dim1_idx=0 → 3, dim2_idx=-1 → treated as 1, 3!=1 → False)

Wait — actually for i=2: `dim1_idx = 3-1-2 = 0`, `dim2_idx = 2-1-2 = -1`.
`dim2 = shape2[-1+1] if -1 >= 0 else 1` → `dim2 = 1`. `dim1 = 3`.
`3 != 1 and 3 != 1 and 1 != 1` → `3 != 1 and 3 != 1 and False` → condition is False.
So the loop does NOT return False for this case. Returns True. That's the bug.

## Fix Applied

```mojo
var ndim1 = len(shape1)
var ndim2 = len(shape2)

# Broadcasting cannot reduce the number of dimensions
if ndim2 < ndim1:
    return False

var max_ndim = max(ndim1, ndim2)
```

## Files Changed

- `shared/core/broadcasting.mojo` — added guard + updated docstring
- `shared/core/shape.mojo` — added clarifying comment in `broadcast_to`
- `tests/shared/core/test_broadcasting_part5.mojo` — new test file (9 tests)

## PR

# 4816 — auto-merge rebase enabled

## Date

2026-03-15
