# Session Notes: mojo-setitem-glibc-hook-skip

## Session Context

- **Date**: 2026-03-05
- **Project**: ProjectOdyssey
- **Branch**: 3165-auto-impl
- **PR**: #3385 (issue #3165)
- **Working directory**: `/home/mvillmow/Odyssey2/.worktrees/issue-3165`

## Raw Problem Description

PR #3385 added three `__setitem__` tests to `tests/shared/core/test_utility.mojo`:

```mojo
t[1] = 9.5          # line 282
t[2] = Int64(7)     # line 294
t[5] = 1.0          # line 307 (out-of-bounds test)
```

CI failed with `error: expression must be mutable in assignment` at all three lines
because `ExTensor.__setitem__` did not exist. Only `__getitem__` existed.

Additionally, pre-commit failed with `1 file reformatted` for `test_utility.mojo` —
but this was the pre-existing committed file, not a new change.

## System Environment

- OS: Linux 5.10.0-37-amd64
- GLIBC version: older than 2.32 (exact version not checked)
- Mojo location: `/home/mvillmow/Odyssey2/.pixi/envs/default/bin/mojo`
- Mojo requirement: GLIBC 2.32, 2.33, 2.34 (all missing)
- Result: Every `pixi run mojo format` / `pixi run mojo test` fails at binary load

## Key Code Discovery

### Internal setter signatures (extensor.mojo)

```mojo
fn _set_float64(self, index: Int, value: Float64):   # plain self, raw pointer mutation
fn _set_float32(self, index: Int, value: Float32):   # plain self
fn _set_int64(self, index: Int, value: Int64):       # plain self
```

These take `self` (not `mut self`) because they mutate through raw pointer arithmetic —
Mojo's ownership system doesn't track pointer writes.

### Dispatch pattern from existing code (lines 2979-2983)

```mojo
if dtype == DType.float16 or dtype == DType.float32 or dtype == DType.float64:
    tensor._set_float64(i, value)
else:
    tensor._set_int64(i, Int(value))
```

### Final __setitem__ implementation

Inserted after `__getitem__(self, index: Int)` at line ~709:

```mojo
fn __setitem__(mut self, index: Int, value: Float64) raises:
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
    self.__setitem__(index, Float64(value))
```

## Pre-commit Hook Analysis

- Hook: `mojo-format` in `.pre-commit-config.yaml`
- Entry: `pixi run mojo format`
- The hook itself is valid — it just can't execute on this host
- `SKIP=mojo-format` is the correct per-CLAUDE.md approach for a broken hook
- All other hooks (trailing-whitespace, end-of-file, check-yaml, check-large-files, etc.) ran fine

## What Remains Uncertain

The `test_utility.mojo` pre-commit reformatting failure: the CI Docker container
reformatted `test_utility.mojo` with `mojo format` — but we couldn't determine which
exact lines changed without running mojo locally. This might self-resolve when mojo
format runs on `extensor.mojo` in CI (which now contains the new `__setitem__` methods),
or it might require a follow-up commit if mojo format still touches `test_utility.mojo`.
