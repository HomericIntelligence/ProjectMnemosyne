---
name: adr-009-test-file-splitting
description: "Split Mojo test files exceeding the ADR-009 limit of \u226410 fn test_\
  \ functions per file to prevent heap corruption. Use when: a test file has >10 fn\
  \ test_ functions, CI fails intermittently with libKGENCompilerRTShared.so crashes,\
  \ or enforcing ADR-009 compliance."
category: ci-cd
date: 2026-03-08
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Trigger** | Mojo test file has >10 `fn test_` functions |
| **Root Cause** | Mojo v0.26.1 heap corruption under high JIT test load |
| **Fix** | Split file into ≤8-test chunks, add ADR-009 header, update references |
| **ADR** | `docs/adr/ADR-009-heap-corruption-workaround.md` |
| **CI Impact** | Reduces intermittent `Shared Infra` CI group failures |

## When to Use

1. A Mojo test file contains more than 10 `fn test_` functions
2. CI is non-deterministically failing with `libKGENCompilerRTShared.so` JIT fault
3. Running `grep -c "^fn test_" <file>.mojo` returns >10
4. Implementing ADR-009 compliance as part of a CI stability effort
5. A PR review flags a test file for exceeding the per-file test limit

## Verified Workflow

### Step 1: Count tests in the file

```bash
grep -c "^fn test_" tests/path/to/test_foo.mojo
```

If count > 10, proceed with split. Target ≤8 per file for safety margin.

### Step 2: Determine split boundary

Aim for thematic groupings:

- Part 1: Core functionality tests + supporting tests (up to 8)
- Part 2: Remaining tests (edge cases, interface tests, etc.)

### Step 3: Create part1 file

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from test_foo.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
"""Unit tests for Foo (Part 1).
...
"""
# ... imports ...

# All test functions from the first group

fn main() raises:
    """Run foo tests part 1."""
    test_foo_init()
    # ...
    print("\nAll foo part 1 tests passed! ✓")
```

### Step 4: Create part2 file

Same ADR-009 header comment. Include remaining tests and a `main()` that runs only those.

### Step 5: Delete original file

```bash
git rm tests/path/to/test_foo.mojo
```

### Step 6: Update `validate_test_coverage.py`

Replace the single entry with two entries:

```python
# Before
"tests/path/to/test_foo.mojo",

# After
"tests/path/to/test_foo_part1.mojo",
"tests/path/to/test_foo_part2.mojo",
```

### Step 7: Check CI workflow (usually no change needed)

If the CI pattern uses a glob like `training/test_*.mojo`, no update is needed — both
new files are picked up automatically. Only update the workflow if specific filenames
were hardcoded.

### Step 8: Verify counts

```bash
grep -c "^fn test_" tests/path/to/test_foo_part1.mojo  # should be ≤8
grep -c "^fn test_" tests/path/to/test_foo_part2.mojo  # should be ≤8
```

### Step 9: Commit

```bash
git add tests/path/to/test_foo_part1.mojo tests/path/to/test_foo_part2.mojo
git add tests/path/to/test_foo.mojo  # deleted
git add scripts/validate_test_coverage.py
git commit -m "fix(ci): split test_foo.mojo to fix ADR-009 heap corruption"
```

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| **Max tests per file** | 10 (ADR-009 hard limit) |
| **Target per file** | ≤8 (2-test safety margin) |
| **Mojo version affected** | v0.26.1 |
| **Crash signature** | `libKGENCompilerRTShared.so` JIT fault |
| **CI group affected** | Shared Infra & Testing |
| **CI failure rate** | ~65% of runs before fix (13/20) |

## ADR-009 Header Template

Every split file must include this comment block immediately after the file-level docstring
comment (or at the very top if no docstring):

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from test_<original>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Updating CI workflow pattern | Changed `training/test_*.mojo` glob in `comprehensive-tests.yml` | Not needed — glob already matched new filenames automatically | Check if CI uses globs before editing workflow YAML |
| Keeping 9 tests in part1 | Splitting 11 tests as 9+2 | Violates the ≤8 target (safety margin from ADR-009 limit) | Always target ≤8, not just ≤10, to leave a buffer |
| Renaming without adding ADR header | Creating split files without the required comment | Would fail code review and not communicate intent to future maintainers | Always add the ADR-009 header — it's a required convention |
