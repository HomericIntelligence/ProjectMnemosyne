---
name: adr009-glob-pattern-auto-pickup
description: 'When splitting Mojo test files per ADR-009, check if the CI workflow
  uses a glob pattern before editing it. Use when: (1) splitting test_*.mojo files,
  (2) verifying whether CI workflow needs updating after a split, (3) avoiding unnecessary
  workflow edits.'
category: ci-cd
date: 2026-03-08
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
|-----------|-------|
| **Problem** | ADR-009 splits produce new `test_*_part1.mojo` / `test_*_part2.mojo` files; the issue description may say "update CI workflow" but the workflow may already pick them up via glob |
| **Solution** | Always grep the workflow for the original filename first; if only a glob pattern exists (e.g. `training/test_*.mojo`), no workflow edit is needed |
| **ADR Reference** | ADR-009 in `docs/adr/ADR-009-heap-corruption-workaround.md` |
| **Key Insight** | `test_rmsprop_part1.mojo` and `test_rmsprop_part2.mojo` both match `training/test_*.mojo` — the split is transparent to CI |

## When to Use

- Implementing an ADR-009 test file split and the issue says "update CI workflow"
- Splitting any `test_*.mojo` file and unsure whether the CI workflow hardcodes the filename
- Verifying whether `validate_test_coverage.py` or CI workflows need manual filename updates after a split

## Verified Workflow

### 1. Check if CI workflow hardcodes the filename

```bash
# Search for the exact filename in the workflow
grep -i "test_rmsprop" .github/workflows/comprehensive-tests.yml
# If no match → the workflow uses a glob pattern → no edit needed
```

### 2. Check if the workflow uses a glob pattern

```bash
grep -A2 "Shared Infra" .github/workflows/comprehensive-tests.yml
# Example output:
#   pattern: "training/test_*.mojo testing/test_*.mojo"
# → Glob pattern: split files are automatically discovered
```

### 3. Only update validate_test_coverage.py

`validate_test_coverage.py` maintains an explicit list of excluded files (dataset-dependent tests).
If the original file is in this list, replace it with the two new part files:

```python
# Before
"tests/shared/training/test_rmsprop.mojo",

# After
"tests/shared/training/test_rmsprop_part1.mojo",
"tests/shared/training/test_rmsprop_part2.mojo",
```

```bash
# Verify the file is in the exclusion list
grep -n "test_rmsprop" scripts/validate_test_coverage.py
```

### 4. Decision tree

```text
grep the original filename in comprehensive-tests.yml
├── Found (hardcoded) → edit workflow to reference both new files
└── Not found → check for glob pattern covering the directory
    ├── Glob pattern exists (training/test_*.mojo) → NO workflow edit needed
    └── No pattern at all → add glob pattern or explicit filenames
```

### 5. Split file naming convention

```text
test_rmsprop.mojo (11 tests)
  → test_rmsprop_part1.mojo (8 tests)   # ≤8 per ADR-009 target
  → test_rmsprop_part2.mojo (3 tests)   # remaining tests
```

Each split file must include the ADR-009 header comment:

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from test_rmsprop.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Editing CI workflow | Started editing `comprehensive-tests.yml` to add new filenames to the `Shared Infra` group | Unnecessary — the workflow already uses `training/test_*.mojo` glob pattern | Always grep for the exact filename before editing the workflow |
| Trusting issue description | Issue said "Update `.github/workflows/comprehensive-tests.yml` to reference the new filenames" | The glob pattern already covered it; the description was written defensively | Issue descriptions can be overly cautious — verify actual workflow content |

## Results & Parameters

**Session**: Split `test_rmsprop.mojo` (11 tests) into `test_rmsprop_part1.mojo` (8) + `test_rmsprop_part2.mojo` (3)

**Files changed**:

```text
tests/shared/training/test_rmsprop.mojo          → deleted
tests/shared/training/test_rmsprop_part1.mojo    → created (8 fn test_)
tests/shared/training/test_rmsprop_part2.mojo    → created (3 fn test_)
scripts/validate_test_coverage.py                → updated exclusion list
# .github/workflows/comprehensive-tests.yml      → NOT edited (glob covers it)
```

**CI workflow pattern** (no edit needed):

```yaml
- name: "Shared Infra & Testing"
  pattern: "test_imports.mojo test_data_generators.mojo ... training/test_*.mojo ..."
```

**Pre-commit hooks all passed**: mojo format, mypy, ruff, validate-test-coverage, trailing-whitespace, end-of-file-fixer
