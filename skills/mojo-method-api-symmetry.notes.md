# Session Notes — mojo-method-api-symmetry

## Session Context

- **Date**: 2026-03-15
- **Issue**: ProjectOdyssey #3804 — Add `split_with_indices` method wrapper to ExTensor
- **Branch**: `3804-auto-impl`
- **PR**: #4803

## Objective

Issue #3804 was a follow-up to #3243 (which implemented `split` and `split_with_indices` free
functions in `shared.core.shape`). During #3243 both functions were exported from `shared.core`,
but only `split` received a method wrapper on `ExTensor`. This issue added the missing
`split_with_indices` method wrapper (and also added `split` method wrapper since it was similarly
missing).

## Steps Taken

1. Read `.claude-prompt-3804.md` to understand task scope
2. Explored codebase: found `extensor.mojo`, `shape.mojo`, `__init__.mojo`, test files
3. Identified `split_with_indices` in `shape.mojo` (lines 701-779)
4. Found that `test_extensor_method_api.mojo` was a skip stub (no real tests)
5. Located insertion point: after `broadcast_to` method (last method in ExTensor struct)
6. Observed inline import pattern from `broadcast_to` method
7. Added both `split` and `split_with_indices` method wrappers
8. Rewrote test file with 5 real tests
9. Hit `assert_value_at` type error — fixed by using `message=` keyword arg
10. Hit `mojo test` subcommand error — fixed by using `mojo <file>` directly
11. All 5 tests passed; committed and pushed PR

## Key Files

- `shared/core/extensor.mojo` — ExTensor struct, added methods at lines ~3305-3370
- `shared/core/shape.mojo` — Free functions `split()` and `split_with_indices()`
- `shared/core/__init__.mojo` — Exports both free functions (lines 181-182)
- `tests/shared/core/test_extensor_method_api.mojo` — Replaced stub with 5 tests
- `shared/testing/assertions.mojo` — `assert_value_at` signature (line 649)

## Gotchas

### assert_value_at signature

```mojo
fn assert_value_at(
    tensor: ExTensor,
    index: Int,
    expected: Float64,
    tolerance: Float64 = TOLERANCE_DEFAULT,  # ← 4th arg, NOT message
    message: String = "",
) raises:
```

Passing a string as 4th positional arg fails silently with a confusing type error.
Must use `message=` keyword. Many existing test files (test_shape_part2.mojo) have
this bug — don't copy those patterns.

### mojo test subcommand

Mojo v0.26.1 does not have a `test` subcommand. Use `pixi run mojo <file.mojo>` directly.

### Worktree PIXI_PROJECT_MANIFEST warning

When running pixi commands from a worktree, set the env var explicitly:
```bash
PIXI_PROJECT_MANIFEST=/path/to/worktree/pixi.toml pixi run mojo <file>
```
The WARN is non-fatal but the correct manifest should be used.

### GLIBC incompatibility — SKIP=mojo-format

The pre-commit `mojo-format` hook requires exact Mojo version. On hosts with GLIBC mismatch,
use `SKIP=mojo-format` when committing. This is documented in the project's
`docs/dev/mojo-glibc-compatibility.md`.

## Outcome

- PR #4803 created and auto-merge enabled
- 5 tests all pass
- Zero regressions in `test_shape.mojo`
