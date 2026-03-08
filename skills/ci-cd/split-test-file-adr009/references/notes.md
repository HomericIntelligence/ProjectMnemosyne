# Session Notes: split-test-file-adr009

## Issue

GitHub issue #3427 — `tests/shared/test_imports.mojo` had 24 `fn test_` functions,
exceeding ADR-009 limit of ≤10. This caused intermittent CI heap corruption crashes
(libKGENCompilerRTShared.so JIT fault) in the Shared Infra CI group.

## Files Changed

- Deleted: `tests/shared/test_imports.mojo` (24 tests)
- Created: `tests/shared/test_imports_part1.mojo` (8 tests: Core + Training schedulers/optimizers/metrics)
- Created: `tests/shared/test_imports_part2.mojo` (8 tests: Training callbacks/loops, Data, Utils logging)
- Created: `tests/shared/test_imports_part3.mojo` (8 tests: Utils viz/config, Root, Nested, Version)
- Updated: `.github/workflows/comprehensive-tests.yml` Shared Infra pattern

## PR

#4201 on HomericIntelligence/ProjectOdyssey

## Key Decisions

- Grouped tests by logical package sections for clean splits
- Targeted ≤8 per file (not just ≤10) for safety buffer
- Each file gets its own `fn main()` runner with only its own tests
- CI workflow used a space-separated pattern string — simple string replacement to swap filename
- Pre-commit hooks passed cleanly on first commit attempt
