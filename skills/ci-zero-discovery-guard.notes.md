# Session Notes: CI Zero-Discovery Guard

## Session Context

- **Date**: 2026-03-07
- **Issue**: ProjectOdyssey #3356 — Merge 'Autograd & Benchmarking' group uses parent path - verify glob
- **PR**: ProjectOdyssey #3996
- **Branch**: 3356-auto-impl

## Problem Description

The GitHub Actions CI matrix in `.github/workflows/comprehensive-tests.yml` had a merged entry:

```yaml
- name: "Autograd & Benchmarking"
  path: "tests/shared"
  pattern: "autograd/test_*.mojo benchmarking/test_*.mojo"
```

This used `tests/shared` (the parent directory) as the path, with subdirectory glob patterns.
The `just test-group` recipe expanded these into full paths by prepending `tests/shared/`.

The hazard: if either `tests/shared/autograd/` or `tests/shared/benchmarking/` was empty,
renamed, or moved, the glob expansion would find 0 files. The recipe's empty-file check
then did `exit 0` — a silent false-pass. CI would show green even though no tests ran.

## Root Cause in justfile

```bash
# justfile lines 494-497 (BEFORE fix):
if [ -z "$test_files" ]; then
    echo "⚠️  No test files found"
    exit 0   # <-- silent false-pass
fi
```

## Fix Applied

### 1. justfile — exit guard

Changed `exit 0` to `exit 1` with descriptive error:

```bash
if [ -z "$test_files" ]; then
    echo "❌ ERROR: No test files found in {{path}} matching {{pattern}}"
    echo "   This usually means the directory is empty or was renamed."
    echo "   Fix: update the test group path/pattern in comprehensive-tests.yml"
    exit 1
fi
```

### 2. comprehensive-tests.yml — split matrix entry

Replaced the merged parent-path entry with two specific-path entries:

```yaml
# Added explanatory comment block:
# Kept as separate entries (not merged under tests/shared parent path)
# to avoid silent pass-with-0-tests if a subdirectory is empty/renamed.
# See: https://github.com/homericintelligence/projectodyssey/issues/3356
- name: "Autograd"
  path: "tests/shared/autograd"
  pattern: "test_*.mojo"
- name: "Benchmarking"
  path: "tests/shared/benchmarking"
  pattern: "test_*.mojo"
```

## Continue-on-error Verification

The workflow already had:
```yaml
continue-on-error: ${{ matrix.test-group.name == 'Integration Tests' || matrix.test-group.name == 'Core Tensors' || matrix.test-group.name == 'Benchmarking' }}
```

This already used `'Benchmarking'` (not `'Autograd & Benchmarking'`), so it correctly
matches the new standalone "Benchmarking" entry without any change.

## Files Changed

- `justfile`: Lines 494-499
- `.github/workflows/comprehensive-tests.yml`: Lines 219-226

## Pre-commit Results

All hooks passed:
- Mojo Format: Skipped (no .mojo files changed)
- Validate Test Coverage: Passed
- Check YAML: Passed
- Trim Trailing Whitespace: Passed
- Fix End of Files: Passed
- Fix Mixed Line Endings: Passed

## Related Skills

- `ci-cd/consolidate-ci-matrix`: The inverse pattern — merging CI groups to reduce overhead.
  Our fix is the opposite: splitting merged groups for safety.
- `ci-cd/mojo-flaky-segfault-mitigation`: Related `continue-on-error` usage in same workflow.