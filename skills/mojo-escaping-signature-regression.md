---
name: mojo-escaping-signature-regression
description: "OBSOLETE IN 0.26.3. Fix Mojo escaping fn type parameter regressions (0.26.1 only). In 0.26.3 escaping is removed entirely; use capturing compile-time params instead (see mojo-026-breaking-changes)."
category: ci-cd
date: 2026-03-20
version: "1.1.0"
user-invocable: false
tags: [mojo, escaping, gradient-checker, function-signatures, type-mismatch, build-failure, obsolete-026-3]
---

> **⚠️ OBSOLETE IN MOJO 0.26.3**: The `escaping` keyword is completely removed in 0.26.3.
> This skill applies to Mojo 0.26.1 only. For 0.26.3, see
> [mojo-026-breaking-changes](./mojo-026-breaking-changes.md) — use compile-time
> `capturing` parameters instead of `escaping` runtime parameters.

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-20 |
| **Objective** | Fix build-blocking regression caused by removing `escaping` from shared library fn type parameters |
| **Outcome** | Restored `escaping` on 3 gradient_checker functions, converted test helpers to local escaping closures |

## When to Use

- Build fails with type mismatch on `fn (ExTensor) raises -> ExTensor` vs `fn (ExTensor) raises escaping -> ExTensor`
- `layer_testers.mojo` or any file passing closures to `gradient_checker.mojo` functions fails to compile
- After a commit that "cleaned up" function signatures by removing `escaping`
- `check_gradients`, `check_gradients_verbose`, or `compute_numerical_gradient` callers break

## Verified Workflow

### Quick Reference

```bash
# 1. Check which functions lost escaping
grep -n 'fn check_gradients\|fn check_gradients_verbose\|fn compute_numerical_gradient' <project-root>/shared/testing/gradient_checker.mojo

# 2. Verify callers expect escaping
grep -rn 'escaping' <project-root>/shared/testing/layer_testers.mojo <project-root>/tests/shared/testing/

# 3. Restore escaping on all 3 functions in gradient_checker.mojo
# 4. Convert test helpers to local escaping closures
# 5. Verify: just build
```

### Step 1: Identify the Regression

When `<package-manager> build` fails after modifying `gradient_checker.mojo`, check if `escaping` was removed from the 3 public function signatures:

- `check_gradients(forward_fn: fn (ExTensor) raises escaping -> ExTensor, ...)`
- `check_gradients_verbose(forward_fn: fn (ExTensor) raises escaping -> ExTensor, ...)`
- `compute_numerical_gradient(forward_fn: fn (ExTensor) raises escaping -> ExTensor, ...)`

### Step 2: Restore `escaping` in gradient_checker.mojo

All 3 functions take fn type parameters that MUST have `escaping` because `layer_testers.mojo` passes escaping closures to them.

```mojo
# CORRECT - escaping required
fn check_gradients(
    forward_fn: fn (ExTensor) raises escaping -> ExTensor,
    backward_fn: fn (ExTensor, ExTensor) raises escaping -> ExTensor,
    ...

# WRONG - breaks all callers passing escaping closures
fn check_gradients(
    forward_fn: fn (ExTensor) raises -> ExTensor,
    backward_fn: fn (ExTensor, ExTensor) raises -> ExTensor,
    ...
```

### Step 3: Fix Test Files That Define Top-Level Helpers

Test files with top-level helper functions (non-escaping by default) that are passed to `check_gradients` (which expects `escaping`) need conversion to local closures:

```mojo
# BEFORE (breaks): top-level non-escaping helper
fn simple_square(x: ExTensor) raises -> ExTensor:
    ...

fn test_foo() raises:
    var passed = check_gradients(simple_square, ...)  # TYPE MISMATCH

# AFTER (works): local escaping closure
fn test_foo() raises:
    fn simple_square(x: ExTensor) raises escaping -> ExTensor:
        ...
    var passed = check_gradients(simple_square, ...)  # OK
```

### Step 4: Verify

```bash
just build  # Package compilation should succeed
```

### Critical Rule

**ALWAYS check ALL callers when modifying shared library function signatures.** Pre-commit hooks and `mojo format` do NOT catch cross-file type mismatches -- only full package compilation (`mojo build`) does.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Remove `escaping` from gradient_checker.mojo | Removed `escaping` from 3 fn type params to simplify signatures | Broke `layer_testers.mojo` which passes escaping closures -- type mismatch at build time | `escaping` is part of the fn type; removing it is a breaking API change |
| Top-level test helpers without `escaping` | Defined helpers as top-level `fn foo(x: ExTensor) raises -> ExTensor` | Top-level fns are non-escaping by default; can't pass to `escaping` fn params | Convert to local closures with explicit `escaping` annotation |
| VGG16 output range test with `ones` input | Used `ones(input_shape, DType.float32)` for deep network forward pass | Values overflow to `inf` through 16 conv+ReLU + 3 FC layers | Use `full(input_shape, 0.01, DType.float32)` for deep networks |

## Results & Parameters

### Mojo `escaping` Rules Summary

```text
- Top-level fn: non-escaping by default
- Nested fn (closure): non-escaping by default, add `escaping` explicitly
- fn type parameter: `escaping` is part of the type signature
- Mismatch between escaping/non-escaping = compile error
- Only `mojo build` catches cross-file mismatches (not pre-commit)
```

### Key Callers of gradient_checker.mojo

```text
- shared/testing/layer_testers.mojo         -- passes escaping closures (8+ call sites)
- tests/shared/testing/test_gradient_checker_meta_part1.mojo  -- defines escaping helpers
- tests/shared/testing/test_gradient_checker_meta_part2.mojo  -- defines escaping helpers
- tests/shared/testing/test_gradient_checker_noncont_tensors.mojo -- local escaping closures
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PR #4994 CI fix round 2 | Commit 2e52580d restored escaping and fixed VGG16 overflow |
