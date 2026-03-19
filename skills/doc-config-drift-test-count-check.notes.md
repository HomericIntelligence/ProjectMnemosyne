# Raw Notes: doc-config-drift-test-count-check

## Session Details

- **Date**: 2026-03-02
- **Issue**: ProjectScylla #1226
- **PR**: ProjectScylla #1315
- **Branch**: `1226-auto-impl`

## Problem Statement

`check_doc_config_consistency.py` validated coverage thresholds and `--cov=` paths but had
no check for README.md test count mentions (e.g. `3,500+ tests`). These drift silently as
tests are added, making the README misleading.

## Implementation Approach

Added two functions following the existing `check_X` / `extract_X` pattern:

1. `collect_actual_test_count(repo_root)` — subprocess caller, returns `int | None`
2. `check_readme_test_count(repo_root, actual_count, tolerance)` — pure checker, returns `list[str]`

The check is skipped (not failed) when pytest is unavailable to avoid blocking the script
in environments without the test runner installed.

## Key Observations

### pytest --collect-only output formats

Observed across Python versions:
- `3601 tests collected` (most common)
- `5 tests selected` (with `-k` filters)
- `1 test collected` (singular)
- Summary line in stderr when warnings are present

The regex `r"(\d+)\s+(?:tests?\s+)?(?:selected|collected)"` handles all variants.

### Patch target matters

When mocking `subprocess.run` in tests, the patch target must be the module where it's
**imported and used**, not the stdlib location:

```python
# CORRECT
patch("scripts.check_doc_config_consistency.subprocess.run", ...)

# WRONG — patches stdlib but script already imported subprocess
patch("subprocess.run", ...)
```

### Integration test breakage pattern

When adding a new check to `main()`, all existing integration tests that call `main()`
will run the new check. If the new check can fail on the test's synthetic repo, the old
tests will start failing. Fix by either:
1. Mocking the new check's data collector
2. Ensuring `_make_repo()` generates inputs that pass the new check by default

## Commit Messages Used

```
feat(scripts): extend drift check to cover README.md test count mentions

Add Check 4 to check_doc_config_consistency.py that extracts test count
claims from README.md (e.g. '3,500+ tests') and validates them against
the actual count from `pytest --collect-only -q`. Flags counts that
differ by more than 10%. Gracefully skips the check when pytest is
unavailable (returns None) so the script never exits 1 on infra failures.

Closes #1226
```