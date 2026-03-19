# Session Notes: mojo-if-true-scope-fix

## Context

- Project: HomericIntelligence/ProjectOdyssey
- Issue: #4523
- PR: #4890
- Date: 2026-03-15
- Branch: 4523-auto-impl

## Error Messages Fixed

```text
tests/shared/core/test_memory_leaks.mojo:79:8: error: if statement with constant condition 'if True'
tests/shared/core/test_memory_leaks_part1.mojo:59:8: error: if statement with constant condition 'if True'
tests/shared/core/test_memory_leaks_part2.mojo:86:8: error: if statement with constant condition 'if True'
tests/shared/core/test_memory_leaks_part3.mojo:80:8: error: if statement with constant condition 'if True'
```

## Files Modified

- tests/shared/core/test_memory_leaks.mojo: 7 instances → 0 (6 helpers added)
- tests/shared/core/test_memory_leaks_part1.mojo: 5 instances → 0 (5 helpers added)
- tests/shared/core/test_memory_leaks_part3.mojo: 1 instance → 0 (1 helper added)
- tests/shared/core/test_memory_leaks_part2.mojo: already clean

## Why This Pattern Existed

Memory leak tests validate reference counting by:

1. Creating a tensor (refcount = 1)
2. Copying it in an inner scope (refcount = 2)
3. Letting inner scope exit (refcount drops back to 1)
4. Verifying the refcount returned to 1

The `if True:` block was used to create that inner scope explicitly.

## The Fix

Named helper functions create scope boundaries. When a Mojo function returns,
all variables declared inside are destroyed in reverse order of declaration.
This is identical to block scope exit for ownership/destruction semantics.

## Commit

```text
fix(tests): replace 'if True' scopes with helper functions in memory leak tests

Mojo now warns on constant conditions (--Werror) which caused compilation
failures in test_memory_leaks*.mojo files. Extracted each `if True:` block
into a named helper function to create explicit inner scopes for testing
reference counting behavior.

Closes #4523
```