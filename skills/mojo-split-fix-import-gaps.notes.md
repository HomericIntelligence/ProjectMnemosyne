# Session Notes: mojo-split-fix-import-gaps

## Session Details

- **Date**: 2026-03-08
- **Issue**: #3638 — Split `test_mobilenetv1_e2e.mojo` (11 tests) per ADR-009
- **Branch**: `3638-auto-impl`
- **PR**: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4452

## What Happened

1. Read issue #3638: split `tests/models/test_mobilenetv1_e2e.mojo` (11 fn test_ functions,
   limit is 10 per ADR-009) into 2 files of ≤8 tests each.

2. Read the original file. Noted standard import block:
   ```mojo
   from shared.core.extensor import ExTensor, zeros, ones, full
   ```

3. Noticed `randn()` used in two test functions (`test_mobilenetv1_forward_for_classification`
   and `test_mobilenetv1_training_step_simulation`) without being in the top-level import.

4. Confirmed `randn` is exported by `shared.core.extensor` (grepped the module file).

5. Other e2e test files (e.g., `test_vgg16_e2e.mojo`) correctly include `randn` in their import:
   ```mojo
   from shared.core.extensor import ExTensor, zeros, ones, full, randn
   ```

6. Created part1 (8 tests) and part2 (3 tests), both with corrected `randn` import.

7. Updated `scripts/validate_test_coverage.py` exclude list (1 entry → 2 entries).

8. Deleted original file. All pre-commit hooks passed.

## Key Observation

The original `test_mobilenetv1_e2e.mojo` had a latent import bug: `randn` was used but not
explicitly imported. Mojo compiled and ran it anyway (likely via transitive JIT context).
When creating isolated split files, the gap becomes visible — and must be fixed.

This is a pattern to watch for in any file split: the original can have "hidden" dependencies
that only matter when the file is isolated.

## Files Changed

- DELETED: `tests/models/test_mobilenetv1_e2e.mojo`
- CREATED: `tests/models/test_mobilenetv1_e2e_part1.mojo` (8 tests)
- CREATED: `tests/models/test_mobilenetv1_e2e_part2.mojo` (3 tests)
- MODIFIED: `scripts/validate_test_coverage.py` (updated exclude list)