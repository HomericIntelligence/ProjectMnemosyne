---
name: adr009-test-file-splitting
description: "Workflow for splitting Mojo test files that exceed ADR-009 ≤10 fn test_ limit. Use when: CI has heap corruption failures, a test file has >10 fn test_ functions, or any CI group fails intermittently due to heap corruption."
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
| Time | ~30 minutes |

Splits Mojo test files that exceed ADR-009's ≤10 `fn test_` hard limit and ≤8 target per file,
to prevent Mojo v0.26.1 heap corruption (`libKGENCompilerRTShared.so` JIT fault) in CI.

## When to Use

- A Mojo test file has more than 10 `fn test_` functions
- Any CI group fails intermittently due to heap corruption (13/20 runs is a strong signal)
- A new large test file is being added that would exceed the limit
- ADR-009 compliance check fails in PR review

## Verified Workflow

### 1. Audit existing split state

Check if splitting has already started before creating new files:

```bash
# Count actual test functions (use [a-z] to avoid matching comments)
grep -c "^fn test_[a-z]" tests/shared/testing/test_assertions_*.mojo

# Check for stale deprecated artifacts
ls tests/shared/testing/*.DEPRECATED 2>/dev/null
```

### 2. Identify over-limit files

Files with >10 tests violate ADR-009 hard limit. Files with >8 tests exceed the target.
Target: ≤8 per file (buffer below the 10-test limit that triggers heap corruption).

### 3. Group tests logically for split files

Move tests that form a coherent group (e.g., `assert_equal_int` tests from a float file,
`assert_type` tests from a tensor_values file). Prefer semantic groupings over arbitrary splits.

For a simple 2-way split of a single file, group by test theme:

- Part 1: creation, basic behavior, edge cases
- Part 2: advanced scenarios, error handling, determinism

### 4. Create new split file with ADR-009 header

Each new file must include the ADR-009 comment in its module docstring:

```mojo
"""Tests for <description> - Part N: <theme>.

# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_file>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md

Tests <ComponentName> which <description>.
"""
```

### 5. Delete the original file (simple 2-way split)

When replacing a single file with two new files:

```bash
git rm <original_file>.mojo
```

The new `_part1.mojo` and `_part2.mojo` files replace it entirely.

### 6. Verify counts and CI coverage

```bash
# Verify no file exceeds 10 (count actual functions, not comments)
grep -c "^fn test_[a-z]" <directory>/test_<name>_part*.mojo

# CI glob auto-picks up new files if named test_*.mojo in the right directory
# Check the CI workflow pattern for the affected group - usually no changes needed
```

### 8. Commit and push

All pre-commit hooks must pass (mojo format, test coverage validation).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `grep "^fn test_"` to count tests | Counted comment lines matching the pattern | ADR-009 header comment contained `fn test_` text at line start | Use `^fn test_[a-z]` pattern instead |
| Expecting 61 tests in split files | Issue description said 61 tests | The actual split files in main had 59 tests (issue count was approximate) | Always verify against actual code, not issue description |

## Results & Parameters

**ADR-009 limits:**

- Hard limit: ≤10 `fn test_` per file (heap corruption threshold)
- Target: ≤8 per file (safety buffer)

**CI glob pattern** (no changes needed for new files with `test_` prefix):

```yaml
# Testing Fixtures group
pattern: "testing/test_*.mojo"

# Data Samplers group (part of broader Data group)
pattern: "test_*.mojo datasets/test_*.mojo samplers/test_*.mojo transforms/test_*.mojo loaders/test_*.mojo formats/test_*.mojo"
```

**Grep pattern for accurate count:**

```bash
grep -c "^fn test_[a-z]" <file>.mojo
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3397, PR #4094 (Testing Fixtures group) | [notes.md](../../references/notes.md) |
| ProjectOdyssey | Issue #3474, PR #4312 (Data Samplers group) | [notes.md](../../references/notes.md) |

**Related:** `docs/adr/ADR-009-heap-corruption-workaround.md`, issue #2942
