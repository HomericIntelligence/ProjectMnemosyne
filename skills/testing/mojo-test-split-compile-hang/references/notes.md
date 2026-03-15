# Session Notes — mojo-test-split-compile-hang

## Context

- **Issue**: #4526 — fix: test_extensor_slicing_part3 runtime failure and test_alexnet_layers_part4 compilation hang
- **Branch**: 4526-auto-impl
- **Date**: 2026-03-15

## Problem 1: test_extensor_slicing_part3 — Runtime Failure

**Error**: `Unhandled exception caught during execution: Single slice only supported for 1D tensors`

**Root cause**: `test_slice_2d_value_correctness` called `t2d[1:4]` on a 2D tensor. The
`__getitem__(Slice)` overload only handles 1D tensors. The variadic overload
`__getitem__(*slices: Slice)` handles multi-dimensional slicing.

**Fix**: Change `t2d[1:4]` → `t2d[1:4, :]` (multi-dimensional syntax triggers the right overload).

## Problem 2: test_alexnet_layers_part4 — Compilation Hang

**Symptom**: File takes >120s to compile. CI times out.

**Root cause**: Part4 had 8 test functions including `test_fc1_backward_float32` and
`test_fc2_backward_float32`. These instantiate `LayerTester.test_linear_layer_backward` with
large FC layers (9216→4096 and 4096→4096), creating massive template instantiation.
Combined with other tests in the same compilation unit, this triggers what appears to be
a Mojo v0.26.1 compiler issue (possibly related to ADR-009 heap corruption).

**Fix**: Moved both backward tests to part5 (which had only 6 tests, well under the ≤10 limit).
Part4 went from 8→6 tests; part5 went from 6→8 tests.

## Files Changed

- `tests/shared/core/test_extensor_slicing_part3.mojo` — line 82: `t2d[1:4]` → `t2d[1:4, :]`
- `tests/models/test_alexnet_layers_part4.mojo` — removed 2 backward test functions + main() calls
- `tests/models/test_alexnet_layers_part5.mojo` — added 2 backward test functions + main() calls

## PR

PR #4893: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4893
