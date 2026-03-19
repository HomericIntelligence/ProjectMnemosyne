# Session Notes: mojo-trait-conformance-fix

## Session Context

- **Date**: 2026-03-06
- **Repository**: HomericIntelligence/ProjectOdyssey
- **Branch**: `3164-auto-impl`
- **PR**: #3373
- **Issue**: #3164

## Problem

CI failure in `Core Utilities` test group:

```text
tests/shared/core/test_utility.mojo:383
error: no matching function in call to 'hash'
note: argument type 'ExTensor' does not conform to trait 'Hashable'
```

`ExTensor` had `__hash__` implemented (using `bitcast` for exact float bit representation) but
`Hashable` was not listed in its struct declaration at `shared/core/extensor.mojo:46`.

## Fix

Single-line change:

```mojo
# Before (line 46)
struct ExTensor(Copyable, ImplicitlyCopyable, Movable, Sized):

# After (line 46)
struct ExTensor(Copyable, ImplicitlyCopyable, Movable, Sized, Hashable):
```

## Environment Constraints

- Host OS: Debian with GLIBC 2.31
- Mojo requires GLIBC 2.32, 2.33, 2.34
- Result: `mojo` binary cannot run locally — all test verification must go through CI
- Pre-commit `mojo-format` hook fails for same reason
- Workaround: `SKIP=mojo-format git commit ...`
- CI uses Docker image with correct GLIBC — formatting and tests pass there

## Integration Tests Note

The `Integration Tests` CI failure (4 tests crashing with `mojo: error: execution crashed`)
was identified as pre-existing and unrelated to this PR — those files were not modified by
the PR and also crash on `main`.

## Key Insight

In Mojo, implementing a trait's methods is necessary but not sufficient. The trait must also
be explicitly declared in the struct's conformance list. This is different from some languages
where duck typing or implicit interface satisfaction applies.