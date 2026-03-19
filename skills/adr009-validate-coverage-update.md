---
name: adr009-validate-coverage-update
description: 'Update validate_test_coverage.py when splitting Mojo test files per
  ADR-009. Use when: splitting a test file listed in validate_test_coverage.py, pre-commit
  Validate Test Coverage hook fails after a split, or adding/removing tracked test
  files.'
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| Category | ci-cd |
| Complexity | Low |
| Risk | Low |
| Time | ~5 minutes |

When splitting a Mojo test file per ADR-009, `scripts/validate_test_coverage.py` tracks
expected test files by exact path. Failing to update it causes the pre-commit `Validate Test
Coverage` hook to fail with the old filename missing and new filenames unrecognized.

## When to Use

- Splitting a test file that appears in `scripts/validate_test_coverage.py`
- Pre-commit `Validate Test Coverage` hook fails after an ADR-009 file split
- Any test file is renamed, added, or deleted that is tracked in the coverage script

## Verified Workflow

### 1. Check if the file is tracked

```bash
grep "test_metrics" scripts/validate_test_coverage.py
```

If the file appears, it must be updated. If it doesn't appear, no change needed.

### 2. Replace old entry with two new entries

Use a single Edit (not sed) to replace the old filename with both new filenames:

```python
# Before
"tests/shared/training/test_metrics.mojo",

# After
"tests/shared/training/test_metrics_part1.mojo",
"tests/shared/training/test_metrics_part2.mojo",
```

### 3. Verify pre-commit passes

```bash
# Stage all changed files first
git add tests/shared/training/test_metrics_part1.mojo \
        tests/shared/training/test_metrics_part2.mojo \
        tests/shared/training/test_metrics.mojo \
        scripts/validate_test_coverage.py

# Run pre-commit to verify (or just commit — hooks run automatically)
```

### 4. CI workflow check

For CI workflows using glob patterns like `training/test_*.mojo`, new `test_*` files are
automatically picked up — **no workflow changes needed**. Only update workflows that
reference specific filenames explicitly.

```bash
# Verify: does the CI workflow reference the specific filename?
grep "test_metrics" .github/workflows/comprehensive-tests.yml
# If no output → glob picks it up automatically, no change needed
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Skipping validate_test_coverage.py update | Assumed CI workflow was the only file to update | Pre-commit `Validate Test Coverage` hook would fail with deleted filename | Always grep for the filename in `scripts/validate_test_coverage.py` before committing |
| Updating CI workflow unnecessarily | Thought the workflow needed new filenames | CI pattern `training/test_*.mojo` auto-discovers all `test_*.mojo` files | Check if the CI pattern is a glob before editing the workflow |

## Results & Parameters

**Files to always check when splitting a test file:**

1. `scripts/validate_test_coverage.py` — explicit file list, must be updated
2. `.github/workflows/comprehensive-tests.yml` — check if pattern is glob or explicit

**validate_test_coverage.py update pattern:**

```python
# Find the entry
grep "test_original_name" scripts/validate_test_coverage.py

# Update it (replace 1 entry with 2)
"tests/shared/training/test_original.mojo",
# becomes:
"tests/shared/training/test_original_part1.mojo",
"tests/shared/training/test_original_part2.mojo",
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3465, PR #4292 | Split test_metrics.mojo (16 tests → 8+8), updated validate_test_coverage.py |

**Related:** `adr009-test-file-splitting` skill, `docs/adr/ADR-009-heap-corruption-workaround.md`
