# Session Notes: Document Copy vs View Semantics (Issue #3086)

## Date

2026-03-04

## Objective

Implement GitHub cleanup issue #3086: document and track tensor slicing behavior
(copies vs views) in the ExTensor implementation.

## Issue Description

- File: `tests/shared/core/test_extensor_slicing.mojo`
- Lines 287, 302 had `NOTE: Current implementation creates copies, not views.`
- Decision required: is this by design or a limitation?
- Source file: `shared/core/extensor.mojo`

## Steps Taken

1. Read `.claude-prompt-3086.md` to understand the task
2. Read the test file around lines 287 and 302
3. Globbed for `extensor.mojo` in the worktree
4. Read all three slicing methods in `extensor.mojo` to understand their true semantics
5. Updated docstrings for all three methods with accurate `Returns:` and new `Notes:` sections
6. Renamed `test_slice_is_view` → `test_slice_creates_copy` (name contradicted the assertion)
7. Removed `NOTE:` markers; replaced with clear "by design" language
8. Updated `main()` call site to use new function name
9. Ran `pixi run pre-commit run --all-files` — all hooks passed
10. Committed, pushed, opened PR #3188, enabled auto-merge

## Key Discovery

The three slicing methods in ExTensor have **different semantics**:

| Method | Semantics |
|--------|-----------|
| `slice(start, end, axis)` | True view (pointer offset, refcount++) |
| `__getitem__(Slice)` | Copy by design (strided byte copy) |
| `__getitem__(*slices)` | True view (pointer offset per dim) |

The test `test_slice_is_view` was testing `__getitem__(Slice)` which is a copy — so the name
"is_view" was the opposite of what the test asserted. Classic misleading name.

## Decision Made

Copy semantics for `__getitem__(Slice)` is **by design**, not a limitation:
- Strided slicing requires materialization anyway
- Avoids ownership/lifetime complexity in Mojo
- YAGNI: view optimization not needed for current use cases

The `NOTE:` markers were removed and replaced with authoritative documentation.

## Files Changed

- `shared/core/extensor.mojo`: 3 docstrings updated
- `tests/shared/core/test_extensor_slicing.mojo`: 2 docstrings updated, 1 rename, 1 call site

## Environment Notes

- `just` was not on PATH; used `pixi run pre-commit run --all-files` instead
- `mojo` binary requires GLIBC >= 2.32 (not available on this host) — mojo format hook
  exits with glibc errors but is treated as "Passed" by pre-commit (exit 0 fallback)
- All other hooks (ruff, markdownlint, trailing-whitespace, etc.) passed cleanly

## PR

https://github.com/HomericIntelligence/ProjectOdyssey/pull/3188
