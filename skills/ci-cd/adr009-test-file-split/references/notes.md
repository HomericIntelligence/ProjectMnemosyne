# Session Notes: ADR-009 Test File Split

## Date

2026-03-08

## Issue

GitHub issue #3630: `tests/training/test_confusion_matrix.mojo` had 11 `fn test_` functions,
exceeding the ADR-009 limit of ≤10 per file. This caused intermittent heap corruption crashes
(`libKGENCompilerRTShared.so` JIT fault) in the "Shared Infra" CI group.

## Context

- Mojo v0.26.1 has a known heap corruption bug triggered under high test load
- ADR-009 mandates ≤10 `fn test_` functions per file as a workaround
- CI failure rate: 13/20 recent runs on `main` non-deterministically failing
- File had 11 tests; target was ≤8 per split file

## Approach

1. Read the original `tests/training/test_confusion_matrix.mojo` (594 lines, 11 tests)
2. Checked CI workflow `comprehensive-tests.yml` — "Misc Tests" group uses `training/test_*.mojo` wildcard
3. Checked `validate_test_coverage.py` — original file not in any exclude list
4. Created `test_confusion_matrix_part1.mojo` (8 tests: basic, perfect, normalize_row, normalize_column, normalize_total, precision, recall, f1_score)
5. Created `test_confusion_matrix_part2.mojo` (3 tests: with_logits, reset, empty)
6. Both files include ADR-009 header comment in module docstring
7. Deleted original file
8. Committed — all pre-commit hooks passed (including `Validate Test Coverage`)
9. Pushed and created PR #4430

## Key Insight: Wildcard CI Patterns

The CI workflow uses `pattern: "training/test_*.mojo"` which automatically discovers any
`test_*.mojo` file in that directory. This meant:

- No changes to `comprehensive-tests.yml` were needed
- No changes to `validate_test_coverage.py` were needed
- The pre-commit `Validate Test Coverage` hook confirmed coverage automatically

Always check if CI uses wildcards before editing workflows.

## Files Changed

- Deleted: `tests/training/test_confusion_matrix.mojo`
- Created: `tests/training/test_confusion_matrix_part1.mojo` (8 tests)
- Created: `tests/training/test_confusion_matrix_part2.mojo` (3 tests)

## PR

https://github.com/HomericIntelligence/ProjectOdyssey/pull/4430
