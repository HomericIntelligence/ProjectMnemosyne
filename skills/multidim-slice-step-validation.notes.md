# Session Notes: multidim-slice-step-validation

## Session Date
2026-03-15

## Issue
GitHub issue #4463 — `__getitem__(*slices)` in `extensor.mojo` ignored the `step` field of
each `Slice`, so `tensor[::2, :]` silently returned every element instead of every other.

## Repository
`HomericIntelligence/ProjectOdyssey`
Branch: `4463-auto-impl`
PR: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4884

## Root Cause

`__getitem__(self, *slices: Slice)` at line 1044 of `shared/core/extensor.mojo` computed
`start`/`end` from each slice but never read `slice.step`. The 1D overload (`__getitem__(Slice)`)
correctly handles step (including negative step), but the variadic overload did not.

## Fix Applied

Inserted a step-validation loop immediately before the per-dimension computation loop:

```mojo
for dim in range(num_dims):
    var step = slices[dim].step.or_else(1)
    if step != 1:
        raise Error(
            "Multi-dimensional slicing does not support step != 1 "
            + "(got step=" + String(step)
            + " on dimension " + String(dim)
            + "). Use 1D slicing for strided access."
        )
```

Also updated the docstring `Raises` clause.

## Test Coverage

New file: `tests/shared/core/test_extensor_multidim_step.mojo`

- `test_multidim_step2_first_dim_raises` — `t2d[::2, :]` raises
- `test_multidim_step2_second_dim_raises` — `t2d[:, ::2]` raises
- `test_multidim_negative_step_raises` — `t2d[::-1, :]` raises
- `test_multidim_step3_3d_raises` — `t3d[::3, :, :]` raises
- `test_multidim_step1_does_not_raise` — `t2d[::1, ::1]` succeeds
- `test_multidim_no_step_does_not_raise` — `t2d[1:4, 1:3]` succeeds

All 6 pass. Existing 2D slicing tests unaffected.

## Key Patterns

- `slices[dim].step.or_else(1)` — Mojo `Optional[Int]` default extraction
- ADR-009 compliance: ≤10 `fn test_` per file due to heap corruption flake
- `just test-group <path> <pattern>` — project test runner
- Fail-fast over full implementation when issue gives the option