---
name: adr009-test-file-splitting
description: "Workflow for splitting Mojo test files that exceed ADR-009 ≤10 fn test_ limit. Use when: CI has heap corruption failures, a test file has >10 fn test_ functions, or a CI test group fails intermittently."
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
- A CI test group fails intermittently (13/20 runs is a strong signal)
- A new large test file is being added that would exceed the limit
- ADR-009 compliance check fails in PR review

## Verified Workflow

### 1. Audit existing split state

Check if splitting has already started before creating new files:

```bash
# Count actual test functions (use [a-z] to avoid matching comments)
grep -c "^fn test_[a-z]" tests/shared/training/test_optimizers*.mojo

# Check for stale deprecated artifacts
ls tests/shared/training/*.DEPRECATED 2>/dev/null
```

### 2. Identify over-limit files

Files with >10 tests violate ADR-009 hard limit. Files with >8 tests exceed the target.
Target: ≤8 per file (buffer below the 10-test limit that triggers heap corruption).

### 3. Group tests logically for split files

Group tests by optimizer/topic (e.g., SGD + Adam basics in part1, advanced Adam + RMSprop + PyTorch
validation in part2). Prefer semantic groupings over arbitrary splits.

### 4. Create new split files with ADR-009 header

Place the ADR-009 comment at the **top of the file** (before the docstring), not inside it:

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from test_optimizers.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
"""Module docstring describing what tests this file contains.

Split from <original_file>.mojo per ADR-009 to avoid Mojo heap corruption.
"""
```

### 5. Delete the original file

```bash
rm tests/shared/training/test_optimizers.mojo
# Then stage the deletion
git add tests/shared/training/test_optimizers.mojo
```

### 6. Update validate_test_coverage.py if needed

If the original file was in an excluded list in `scripts/validate_test_coverage.py`,
replace it with both new filenames:

```python
# Before:
"tests/shared/training/test_optimizers.mojo",

# After:
"tests/shared/training/test_optimizers_part1.mojo",
"tests/shared/training/test_optimizers_part2.mojo",
```

### 7. Verify counts and CI coverage

```bash
# Verify no file exceeds 10 (count actual functions, not comments)
grep -c "^fn test_[a-z]" tests/shared/training/test_optimizers_part*.mojo

# CI glob auto-picks up new files if named test_*.mojo in the right directory
# No workflow changes needed — the pattern training/test_*.mojo covers both new files
```

### 8. Commit and push

All pre-commit hooks must pass (mojo format, test coverage validation, mypy, ruff).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `grep "^fn test_"` to count tests | Counted comment lines matching the pattern | ADR-009 header comment contained `fn test_` text at line start | Use `^fn test_[a-z]` pattern instead |
| Expecting 61 tests in split files | Issue description said 61 tests | The actual split files in main had 59 tests (issue count was approximate) | Always verify against actual code, not issue description |
| Placing ADR-009 comment inside docstring | Added comment block inside `"""..."""` | Mojo syntax — `#` comments are not valid inside string literals | Place ADR-009 `#` comment block above the docstring at file top |

## Results & Parameters

**ADR-009 limits:**

- Hard limit: ≤10 `fn test_` per file (heap corruption threshold)
- Target: ≤8 per file (safety buffer)

**CI glob pattern** (no changes needed for new files with `test_` prefix):

```yaml
# Both training/test_*.mojo and testing/test_*.mojo patterns auto-cover new files
pattern: "training/test_*.mojo testing/test_*.mojo"
```

**Grep pattern for accurate count:**

```bash
grep -c "^fn test_[a-z]" <file>.mojo
```

**validate_test_coverage.py:** Always check if the original file is referenced in excluded lists
and replace with both new filenames.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3397, PR #4094 | test_assertions split (testing/ directory) |
| ProjectOdyssey | Issue #3464, PR #4291 | test_optimizers split (training/ directory) |

**Related:** `docs/adr/ADR-009-heap-corruption-workaround.md`, issues #2942, #3397, #3464
