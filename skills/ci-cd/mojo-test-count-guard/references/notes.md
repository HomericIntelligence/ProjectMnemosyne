# Session Notes: mojo-test-count-guard

## Context

- **Repository**: ProjectOdyssey
- **Issue**: #3962 — Add test-count guard pre-commit hook per ADR-009 Phase 2
- **PR**: #4841
- **Branch**: `3962-auto-impl`
- **Date**: 2026-03-15

## Background

ADR-009 documented a Mojo 0.26.1 heap-corruption bug that crashes after ~15 cumulative
`fn test_` calls in a single test file. Phase 1 (splitting `test_lenet5_layers.mojo` into
5 files) was complete. Phase 2 (automated enforcement) was the follow-up issue.

## Implementation

### Files Created

- `scripts/check_test_count.py` — guard script
- `tests/test_check_test_count.py` — 21 pytest unit tests
- `.pre-commit-config.yaml` — added `check-test-count` hook

### Script Design Decisions

1. **`re.MULTILINE`**: Required for `^` to match each line start, not just the file start.
   Without it, only the first `fn test_` in the file would be found.

2. **`is_mojo_test_file` filter**: Checks both `.mojo` suffix AND `"tests" in path.parts`
   so production Mojo files with helper functions named `fn test_...` are not flagged.

3. **`pass_filenames: true`**: Pre-commit passes only staged files. No directory walk needed.

4. **Zero dependencies**: Uses only stdlib (`re`, `pathlib`, `sys`). Works with any Python 3.7+.

### Test Coverage (21 tests)

- `TestIsMojoTestFile` (6 tests): mojo under tests/, absolute path, non-mojo extension,
  outside tests/, empty path, bare filename
- `TestCountTestsInFile` (6 tests): normal counting, indented fn, non-test fns, string
  mention ignored, missing file, empty file
- `TestCheckFiles` (9 tests): empty argv, at limit, below limit, above limit, non-test Mojo
  skipped, Python file skipped, mixed files one violation, all pass, LIMIT==10 assertion

### Commit

```
d336dda3 feat(pre-commit): Add test-count guard hook per ADR-009 Phase 2
```

## Key Lessons

- Regex line anchors need `re.MULTILINE` for per-line matching in file content
- Filter on both extension AND directory structure when scoping hooks to test files
- `pass_filenames: true` is the correct pattern for per-file validation hooks
- Write the temp test files under a `tests/` subdirectory in tmpdir so path-based
  filters work correctly in unit tests
