# Session Notes: ADR-009 Test File Split

## Session Date: 2026-03-08

## Context

ProjectOdyssey issue #3629: `tests/configs/test_merging.mojo` had 12 `fn test_` functions,
exceeding the ADR-009 limit of 10. This caused the `Configs` CI group to fail 13/20 recent
runs due to Mojo v0.26.1 heap corruption (`libKGENCompilerRTShared.so` JIT fault).

## Steps Taken

1. Read `.claude-prompt-3629.md` to understand the issue
2. Read `tests/configs/test_merging.mojo` to understand the 12 test functions
3. Read `.github/workflows/comprehensive-tests.yml` to check CI references
4. Checked `scripts/validate_test_coverage.py` — no hardcoded filename references
5. Created `tests/configs/test_merging_part1.mojo` (8 tests)
6. Created `tests/configs/test_merging_part2.mojo` (4 tests)
7. Deleted `tests/configs/test_merging.mojo`
8. Committed (all pre-commit hooks passed)
9. Pushed branch and created PR #4423
10. Enabled auto-merge

## Key Observations

- CI uses `just test-group tests/configs "test_*.mojo"` — glob pattern, no explicit filenames
- `validate_test_coverage.py` does dynamic discovery, not hardcoded filenames
- `mojo format` pre-commit hook ran and passed on new files
- `validate_test_coverage.py` pre-commit hook passed — confirms coverage preserved
- Git staged the deletion as a rename (70% similarity detected automatically)

## Environment

- Mojo version: v0.26.1
- Branch: `3629-auto-impl`
- Worktree: `/home/mvillmow/Odyssey2/.worktrees/issue-3629`
- PR: HomericIntelligence/ProjectOdyssey#4423

## Related

- ADR-009: `docs/adr/ADR-009-heap-corruption-workaround.md`
- Related issue: #2942 (original heap corruption discovery)
- Previous split: `test_gradient_checking` was also split (mentioned in CI workflow comments)

---

# Session Notes: ADR-009 Test File Split

## Session Context

- **Date**: 2026-03-07
- **Issue**: #3416 — fix(ci): split test_tensor_factory.mojo (28 tests) — Mojo heap corruption (ADR-009)
- **Branch**: `3416-auto-impl`
- **PR**: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4166

## Problem

`tests/shared/testing/test_tensor_factory.mojo` contained 28 `fn test_` functions, exceeding
ADR-009's limit of 10 per file. This caused intermittent heap corruption crashes in Mojo v0.26.1
(`libKGENCompilerRTShared.so` JIT fault), with a 13/20 CI failure rate on the `main` branch.

## Solution

Split the 28-test file into 4 files of ≤8 tests each:

- `test_tensor_factory_part1.mojo`: 8 tests (zeros_tensor, ones_tensor)
- `test_tensor_factory_part2.mojo`: 8 tests (full_tensor, random_tensor)
- `test_tensor_factory_part3.mojo`: 8 tests (random_normal_tensor, set_tensor_value first half)
- `test_tensor_factory_part4.mojo`: 4 tests (set_tensor_value second half, integration tests)

## Key Observations

1. **CI glob pattern**: The `comprehensive-tests.yml` workflow uses `testing/test_*.mojo` for the
   "Shared Infra & Testing" group — no workflow changes were needed.

2. **validate_test_coverage.py**: Had no explicit references to `test_tensor_factory.mojo`,
   so no script updates were required.

3. **Pre-commit hooks passed**: Mojo format, validate_test_coverage, and other hooks all
   passed automatically on the split files.

4. **Safety margin**: Targeting ≤8 (not just ≤10) provides buffer below the ADR-009 limit.

5. **Import scoping**: Each split file only imports the functions it tests, keeping imports minimal.

## Commands Used

```bash
# Count tests in original file
grep -c "^fn test_" tests/shared/testing/test_tensor_factory.mojo
# → 28

# Verify counts in split files
grep -c "^fn test_" tests/shared/testing/test_tensor_factory_part*.mojo
# → 8, 8, 8, 4

# Delete original
rm tests/shared/testing/test_tensor_factory.mojo

# Stage and commit
git add tests/shared/testing/test_tensor_factory.mojo tests/shared/testing/test_tensor_factory_part*.mojo
git commit -m "fix(ci): split test_tensor_factory.mojo into 4 files (ADR-009)"

# Push and create PR
git push -u origin 3416-auto-impl
gh pr create --title "fix(ci): split test_tensor_factory.mojo into 4 files (ADR-009)"
gh pr merge --auto --rebase
```

## Related

- ADR-009: `docs/adr/ADR-009-heap-corruption-workaround.md`
- Related issue: #2942
- Sample failing CI run: `22751105525`
