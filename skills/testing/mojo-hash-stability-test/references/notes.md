# Session Notes — mojo-hash-stability-test

## Context

- **Repository**: HomericIntelligence/ProjectOdyssey
- **Issue**: #4069 — "Test hash stability across repeated calls on same empty tensor"
- **Follow-up from**: #3384 (original hash correctness work)
- **Branch**: `4069-auto-impl`
- **Date**: 2026-03-15

## Objective

The existing hash tests for `ExTensor` used two independent tensor instances (`hash(a) == hash(b)`)
to verify equal tensors produce equal hashes. Issue #4069 requested a stronger test: hash the
**same** instance multiple times and assert all results are equal, confirming `__hash__` is
truly deterministic with no side effects for 0-element tensors.

## Steps Taken

1. Read `.claude-prompt-4069.md` for task context.
2. Searched `tests/shared/core/test_utility.mojo` for existing hash test block (line ~667).
3. Identified available helpers: `assert_equal_int`, `full`, `arange`, `ones`, `zeros`.
4. Read lines 790–810 to find exact insertion point after `test_hash_integer_dtype_consistent`.
5. Added `test_hash_stability_repeated_calls()` using a single empty tensor instance.
6. Registered the call in `main()` after `test_hash_same_values_different_dtype()`.
7. Committed with message `test(utility): add hash stability test for repeated calls on same empty tensor`.
8. Pushed branch and created PR #4864.

## What Worked

- Using `var a = full(List[Int](), 0.0, DType.float32)` for an empty 0-element tensor
- Paired `assert_equal_int(Int(hash(a)), Int(hash(a)), "...")` calls to check 3 invocations total
- Following the exact pattern of surrounding tests (helper names, DType choice, shape construction)

## Key Decision

Asserting equality between `hash(a)` calls rather than against a hardcoded expected value,
because hash seeds and dtype ordinals can differ across builds. The goal is stability, not
a specific value.

## PR

- PR #4864: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4864
