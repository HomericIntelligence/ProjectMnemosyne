# Session Notes: mojo-setitem-test-pattern

## Context

- **Repository**: ProjectOdyssey
- **Issue**: #3165 — Add `__setitem__` tests to `test_utility.mojo`
- **Branch**: `3165-auto-impl`
- **PR**: #3385
- **Date**: 2026-03-05

## Objective

Add three missing tests for the new `__setitem__` method on `ExTensor` in
`tests/shared/core/test_utility.mojo`. The method was implemented in the issue-2722
worktree (`shared/core/extensor.mojo:881-919`) but not yet merged to main.

## Implementation Details

### __setitem__ signatures (from issue-2722 worktree)

```mojo
fn __setitem__(mut self, index: Int, value: Float64) raises:
    if index < 0 or index >= self._numel:
        raise Error("Index out of bounds")
    self._set_float64(index, value)

fn __setitem__(mut self, index: Int, value: Int64) raises:
    if index < 0 or index >= self._numel:
        raise Error("Index out of bounds")
    self._set_int64(index, value)
```

### File modified

`tests/shared/core/test_utility.mojo` — extended from 489 to 538 lines

### Insertion point

After line 269 (end of `test_len_1d`), before the `# Test __bool__` section.

### main() update

Added `# __setitem__` block between `__len__` and `__bool__` sections.

## Environment

- Mojo version: v0.26.1 (via pixi)
- GLIBC issue: Host system too old (Debian 10, GLIBC 2.28) — Mojo requires 2.32+
- Verification: CI-only (cannot run locally)

## Commit

`ac35226c` — "test(utility): add __setitem__ tests to test_utility.mojo"