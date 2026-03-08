---
name: adr009-test-file-splitting
description: "Workflow for splitting Mojo test files that exceed ADR-009 ≤10 fn test_ limit. Use when: CI has heap corruption failures, a test file has >10 fn test_ functions, or Testing Fixtures CI group fails intermittently."
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
- CI Testing Fixtures group fails intermittently (13/20 runs is a strong signal)
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

### 4. Create new split file with ADR-009 header

Each new file must include the ADR-009 comment:

```mojo
"""Tests for <description>.

# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from test_assertions.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md

Note: Split from <original_file>.mojo to satisfy ADR-009 ≤8 fn test_ target per file.
"""
```

### 5. Update source file

Remove moved tests from the source file:

- Remove the `fn test_` function definitions
- Remove moved functions from the `main()` call list
- Remove now-unused imports

### 6. Delete stale artifacts

```bash
git rm tests/shared/testing/test_assertions.mojo.DEPRECATED
```

### 7. Verify counts and CI coverage

```bash
# Verify no file exceeds 10 (count actual functions, not comments)
grep -c "^fn test_[a-z]" tests/shared/testing/test_assertions_*.mojo

# CI glob auto-picks up new files if named test_*.mojo in the right directory
# No workflow changes needed for testing/test_*.mojo glob pattern
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
pattern: "testing/test_*.mojo"
```

**Grep pattern for accurate count:**

```bash
grep -c "^fn test_[a-z]" <file>.mojo
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3397, PR #4094 | [notes.md](../../references/notes.md) |
| ProjectOdyssey | Issue #3436, PR #4221 — configs/test_validation.mojo (23 tests → 3 files) | [notes.md](../../references/notes.md) |

**Related:** `docs/adr/ADR-009-heap-corruption-workaround.md`, issue #2942
