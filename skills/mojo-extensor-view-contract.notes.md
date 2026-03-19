# Session Notes: ExTensor View Contract Documentation

**Date**: 2026-03-15
**Issue**: HomericIntelligence/ProjectOdyssey #3802
**PR**: HomericIntelligence/ProjectOdyssey #4802
**Branch**: 3802-auto-impl

## Objective

Add a "view contract" section to `docs/dev/extensor-view-contract.md` covering:

1. Refcount mechanics (`__copyinit__`/`__del__`)
2. `view_with_strides()` — proposed but never implemented
3. When to call `as_contiguous()` (guard pattern, copy semantics, anti-patterns)

## Source Investigation

Grepped `shared/core/extensor.mojo` for `_is_view`, `_refcount`, `__copyinit__`, `__del__`.

Key findings:

- `_refcount` is an `UnsafePointer[Int]`, initialised to 1 in every constructor
- `__copyinit__` increments `_refcount[]` by 1 (shallow copy of pointer, not buffer)
- `__del__` decrements; frees buffer + refcount allocation when `_refcount[] == 0`
- `_is_view` is set to `True` by `reshape`, `transpose`, `slice` — semantic tag only
- Guard pattern already in `matrix.mojo:604-611` (matmul uses `is_contiguous()` check)

## Linting Issues Encountered

### MD060 table-column-style (19 errors initially)

The `markdownlint-cli2` linter uses "aligned" style: all pipe characters must align
column-by-column across header, separator, and data rows.

Root causes:
- `| transpose(dim0, dim1) |` wider than `| Operation |` header
- Mixed column widths within the same table

Fix: manually pad each column to the width of its widest cell.

### MD018 no-missing-space-atx

`#3236` appearing at the start of a line is parsed as an ATX heading (`# heading`).
The linter requires a space after `#` for headings, so it flags the issue-reference.

Fix: replace `#3236` with `issue-3236` when it appears at line start in prose.

## What Worked

- Reading `__copyinit__` and `__del__` directly from source — clearest source of truth
- "guard pattern" framing from the existing matmul code (`matrix.mojo:604-611`)
- Padding markdown tables to aligned style by counting char widths per column

## What Failed

- `#<N>` at sentence start in prose — MD018 false-positive
- Compact table pipes — MD060 requires aligned style
- Initial table padding was partially wrong (one column still misaligned after first fix)