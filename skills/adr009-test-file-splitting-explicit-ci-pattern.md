---
name: adr009-test-file-splitting-explicit-ci-pattern
description: 'ADR-009 test file splitting when CI workflow uses explicit file lists
  instead of test_*.mojo glob. Use when: (1) CI pattern lists specific filenames not
  a glob, (2) splitting explicitly-referenced test files, (3) validate-test-coverage
  hook blocks commit.'
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
| Time | ~20 minutes |

Extends the `adr009-test-file-splitting` workflow for the specific case where the CI matrix
uses an **explicit filename list** (not a `test_*.mojo` glob) to reference test files.

The base `adr009-test-file-splitting` skill says "No workflow changes needed for new files
with `test_` prefix" — but this is only true when the CI pattern uses a glob. When the
pattern lists filenames explicitly (e.g., `testing/test_fixtures_part1.mojo
testing/test_fixtures_part2.mojo`), the workflow MUST be updated.

## When to Use

- Splitting a test file that is **explicitly named** in the CI matrix pattern (not covered by `test_*.mojo`)
- The `validate-test-coverage` pre-commit hook fails because new `test_*.mojo` files are not in the workflow
- CI group pattern looks like `"file1.mojo file2.mojo file3.mojo"` with space-separated names
- You split `test_fixtures.mojo` (or similar) into `_part1`, `_part2`, `_part3` files

## Verified Workflow

### 1. Check whether CI uses glob or explicit list

```bash
grep -A3 "Shared Infra" .github/workflows/comprehensive-tests.yml
```

If the pattern contains specific filenames (not just `test_*.mojo`), the workflow needs updating.

### 2. Split the file per ADR-009 (≤8 tests per file)

Create `_part1.mojo`, `_part2.mojo`, `_part3.mojo` with ADR-009 header at the **top** (before docstring):

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from test_fixtures.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
"""Module docstring here."""
```

Each part file needs:

- Its own imports (only what that file uses)
- Its own `fn main() raises:` calling only its own tests
- The ADR-009 header comment

### 3. Delete the original file

```bash
git rm tests/shared/testing/test_fixtures.mojo
```

### 4. Update the CI workflow explicit pattern

Replace the old filename with the three new part filenames in the `pattern:` field:

```yaml
# Before:
pattern: "... testing/test_fixtures.mojo"

# After:
pattern: "... testing/test_fixtures_part1.mojo testing/test_fixtures_part2.mojo testing/test_fixtures_part3.mojo"
```

Add a comment above the matrix entry explaining the split:

```yaml
# NOTE: testing/test_fixtures.mojo split into 3 parts per ADR-009 (≤10 fn test_ per file)
# to avoid Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so JIT fault)
```

### 5. Verify validate-test-coverage passes

The `validate-test-coverage` pre-commit hook (and CI job) checks that all `test_*.mojo` files
are covered by the workflow. It will fail if the new part files are not in the pattern.

```bash
python scripts/validate_test_coverage.py
```

### 6. Commit (all hooks must pass)

```bash
git add tests/shared/testing/test_fixtures_part*.mojo
git add tests/shared/testing/test_fixtures.mojo  # staged as deleted
git add .github/workflows/comprehensive-tests.yml
git commit -m "fix(ci): split test_fixtures.mojo into 3 files per ADR-009"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assuming glob covers new files | Skipped workflow update expecting `testing/test_*.mojo` to pick up part files | The CI pattern used explicit filenames, not a glob — new files were invisible to CI | Always check if pattern is glob or explicit list before skipping workflow update |
| Placing ADR-009 comment inside docstring | Put the `# ADR-009:` lines inside `"""..."""` | Comments inside string literals are not code comments in Mojo | Place ADR-009 comment block before the docstring, at the very top of the file |

## Results & Parameters

**Split distribution for 20 tests (target ≤8 each):**

| File | Tests | Content |
|------|-------|---------|
| `test_fixtures_part1.mojo` | 8 | SimpleCNN init/forward, LinearModel init/forward, create_test_cnn |
| `test_fixtures_part2.mojo` | 8 | create_linear_model, create_test_input, create_test_targets, assert_tensor_shape, assert_tensor_dtype valid |
| `test_fixtures_part3.mojo` | 4 | assert_tensor_dtype invalid, assert_tensor_all_finite, assert_tensor_not_all_zeros |

**CI pattern update (space-separated explicit names):**

```yaml
pattern: "test_imports.mojo test_data_generators.mojo test_model_utils.mojo test_serialization.mojo utils/test_*.mojo fixtures/test_*.mojo training/test_*.mojo testing/test_fixtures_part1.mojo testing/test_fixtures_part2.mojo testing/test_fixtures_part3.mojo"
```

**Grep to verify test counts:**

```bash
grep -c "^fn test_[a-z]" tests/shared/testing/test_fixtures_part*.mojo
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3446, PR #4245 | [notes.md](../../references/notes.md) |

**Related:** `adr009-test-file-splitting` (base skill), `docs/adr/ADR-009-heap-corruption-workaround.md`
