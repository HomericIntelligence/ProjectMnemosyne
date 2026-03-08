# Session Notes: Mojo Empty Tensor Hash Test

## Session Details

- Date: 2026-03-07
- Issue: HomericIntelligence/ProjectOdyssey#3384
- PR: HomericIntelligence/ProjectOdyssey#4064
- Branch: 3384-auto-impl

## Objective

Add `test_hash_empty_tensor` to verify that a 0-element ExTensor (shape=[0], numel=0) can
be hashed without error and that repeated hashing returns the same value.

## Context

The issue was filed as a follow-up to #3164. The `__hash__` implementation in
`shared/core/extensor.mojo` (lines 2867–2893) loops over `self._numel` elements.
For numel=0 the loop is skipped, leaving the hash determined solely by shape dimensions
and dtype ordinal. No test covered this edge case.

## Key Files

- `shared/core/extensor.mojo` lines 2867–2893: `__hash__` implementation
- `tests/shared/core/test_utility.mojo`: test file where the new test was added

## Implementation

Added `test_hash_empty_tensor()` function and registered it in `main()`.
Total change: +24 lines in one file.

## Pre-commit Results

All hooks passed:

- Mojo Format: Passed
- Check for deprecated List[Type](args) syntax: Passed
- Validate Test Coverage: Passed
- Trim Trailing Whitespace: Passed
- Fix End of Files: Passed
- Check for Large Files: Passed
- Fix Mixed Line Endings: Passed

## GLIBC Environment Note

The local environment (Debian Buster, GLIBC 2.28) cannot run Mojo directly — the pixi
environment requires GLIBC 2.32+. Tests are validated in CI via Docker container
`ghcr.io/homericintelligence/projectodyssey:main`. Local pre-commit hooks (mojo format,
validate-test-coverage) are sufficient to validate the test file structure before push.
