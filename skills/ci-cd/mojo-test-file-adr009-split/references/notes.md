# Session Notes: Mojo Test File ADR-009 Split

## Session Context

- **Date**: 2026-03-08
- **Issue**: #3505
- **PR**: #4382
- **Branch**: `3505-auto-impl`
- **Repo**: `HomericIntelligence/ProjectOdyssey`

## Problem

`tests/shared/data/test_datasets.mojo` contained 13 `fn test_` functions, exceeding the
ADR-009 limit of 10 per file. This caused intermittent heap corruption crashes in
Mojo v0.26.1 (`libKGENCompilerRTShared.so` JIT fault), making the Data CI group fail
non-deterministically at ~65% rate (13/20 recent runs on main).

## Files Changed

- **Deleted**: `tests/shared/data/test_datasets.mojo` (13 tests)
- **Added**: `tests/shared/data/test_datasets_part1.mojo` (8 tests — interface conformance + loader integration)
- **Added**: `tests/shared/data/test_datasets_part2.mojo` (5 tests — edge cases)
- **Updated**: `tests/shared/README.md` — directory listing updated

## Key Observations

1. The CI Data group pattern `test_*.mojo` automatically matches `test_datasets_part1.mojo`
   and `test_datasets_part2.mojo` — no CI YAML change needed.

2. `validate_test_coverage.py` and `check_test_count_badge.py` scripts did not reference
   the specific filename, so no script changes were needed.

3. Pre-commit hooks all passed cleanly: mojo format, markdown lint, validate-test-coverage,
   check-large-files, trailing whitespace, end-of-file-fixer.

4. Git treated the rename intelligently: `rename tests/shared/data/{test_datasets.mojo =>
   test_datasets_part1.mojo} (65%)` — the similarity detection correctly identified the
   relationship.

## CI Workflow Pattern

The `Data` group in `.github/workflows/comprehensive-tests.yml` uses:

```yaml
- name: "Data"
  path: "tests/shared/data"
  pattern: "test_*.mojo datasets/test_*.mojo samplers/test_*.mojo ..."
  continue-on-error: true
```

The `test_*.mojo` glob picks up both new files automatically.

## Commit Message Used

```
fix(ci): split test_datasets.mojo into 2 files to fix heap corruption (ADR-009)
```

## Related

- ADR-009: `docs/adr/ADR-009-heap-corruption-workaround.md`
- Related issue: #2942
- Sample failing CI run: `22755966807`
