---
name: mojo-adr009-file-split
description: "Split Mojo test files exceeding ADR-009 limit (≤10 fn test_ per file) to fix heap corruption CI failures. Use when: (1) CI shows intermittent heap corruption crashes, (2) a test file has >10 fn test_ functions, (3) ADR-009 compliance check fails."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| Category | ci-cd |
| Complexity | Low |
| Risk | Low |
| Time | ~20 minutes |

Splits a single Mojo test file with >10 `fn test_` functions into multiple files, each with ≤10
tests, to prevent Mojo v0.26.1 heap corruption (`libKGENCompilerRTShared.so` JIT fault) in CI.
Applies when the test file uses explicit CI workflow pattern references (not a glob), requiring
the workflow YAML to be updated to name the new files.

## When to Use

- A Mojo test file has more than 10 `fn test_` functions
- CI shows intermittent `libKGENCompilerRTShared.so` heap corruption crashes
- ADR-009 compliance check fails in PR review
- A test group in CI is flaky with no obvious test logic cause

## Verified Workflow

### 1. Count existing test functions

Use the `[a-z]` suffix to avoid matching ADR-009 header comments that contain `fn test_` text:

```bash
grep -c "^fn test_[a-z]" <test-file>.mojo
```

### 2. Plan logical split groups

Group tests by operation type for semantic coherence. Aim for ≤8 per file (safety buffer below
the hard 10-test limit). For a 19-test file, 3 files of 6/6/7 works well.

Example grouping for comparison operator tests:

- Part 1: equal, not_equal (6 tests)
- Part 2: less, less_equal (6 tests)
- Part 3: greater, greater_equal, negatives (7 tests)

### 3. Create each new split file

Each new file must:

1. Contain its own imports
2. Include the ADR-009 header comment in the module docstring
3. Contain its own `fn main()` runner

ADR-009 header comment format:

```mojo
"""Tests for <description>.

# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md

Note: Split from <original_file>.mojo to satisfy ADR-009 ≤10 fn test_ hard limit per file.
"""
```

### 4. Update CI workflow YAML

When the test file is referenced by explicit filename (not a glob) in the CI workflow, replace
the old filename with the new part filenames as space-separated values in the same pattern string:

```yaml
# Before
pattern: "core/test_comparison_ops.mojo"

# After
pattern: "core/test_comparison_ops_part1.mojo test_comparison_ops_part2.mojo test_comparison_ops_part3.mojo"
```

### 5. Delete original file

```bash
git rm <test-path>/<original-file>.mojo
```

### 6. Verify counts and run pre-commit

```bash
# Verify no file exceeds 10 (use [a-z] suffix for accuracy)
grep -c "^fn test_[a-z]" <test-path>/test_<name>_part*.mojo

# Run pre-commit to validate mojo format, YAML, and test coverage
just pre-commit-all
```

`validate_test_coverage.py` will fail if new files are not referenced in CI — this is the
safety net that ensures CI is updated before committing.

### 7. Commit and push

All pre-commit hooks must pass (mojo format, YAML check, test coverage validation).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| None | The first approach worked end-to-end | N/A | Logical grouping by operation + in-place YAML update is straightforward |

## Results & Parameters

**ADR-009 limits:**

- Hard limit: ≤10 `fn test_` per file (heap corruption threshold in Mojo v0.26.1)
- Target: ≤8 per file (safety buffer)

**Split distribution for 19-test file:**

- Part 1: 6 tests, Part 2: 6 tests, Part 3: 7 tests (all well under limit)

**Grep pattern for accurate count (avoids matching ADR-009 header comment text):**

```bash
grep -c "^fn test_[a-z]" <file>.mojo
```

**CI workflow pattern (space-separated filenames in same pattern field):**

```yaml
pattern: "core/test_foo_part1.mojo test_foo_part2.mojo test_foo_part3.mojo"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3454, PR #4270 | [notes.md](../../references/notes.md) |
| ProjectOdyssey | Issue #3635, PR #4444 | `test_base.mojo`: 11 tests → part1 (8 tests) + part2 (3 tests); glob CI pattern; validate_test_coverage.py updated |

**Related:** `docs/adr/ADR-009-heap-corruption-workaround.md`, issue #2942,
skill `adr009-test-file-splitting` (covers glob-pattern CI workflows)
