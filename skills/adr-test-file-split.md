---
name: adr-test-file-split
description: 'Split Mojo test files exceeding ADR-009 fn test_ function limits to
  fix heap corruption CI failures. Use when: a .mojo test file has >10 fn test_ functions
  causing intermittent CI crashes.'
category: ci-cd
date: 2026-03-08
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so JIT fault) under high test load |
| **ADR** | ADR-009 — ≤10 `fn test_` functions per file |
| **Trigger** | File has >10 `fn test_` functions OR CI shows intermittent crashes in test group |
| **Fix** | Split into multiple files of ≤8 tests each with ADR-009 header comment |
| **CI Impact** | Glob patterns (`test_*.mojo`) auto-discover new files — no workflow changes needed |

## When to Use

- A `.mojo` test file has more than 10 `fn test_` functions
- CI shows intermittent `libKGENCompilerRTShared.so` crashes in a test group
- GitHub issue references ADR-009 heap corruption workaround
- `grep -c "^fn test_" <file>.mojo` returns a number > 10

## Verified Workflow

### 1. Count test functions in the file

```bash
grep -c "^fn test_" tests/path/to/test_file.mojo
```

### 2. Plan the split

- Target: ≤8 tests per file (below the 10 limit for safety margin)
- Name new files: `test_<original>_part1.mojo`, `test_<original>_part2.mojo`
- Assign tests logically (e.g., by feature area, not just sequential)

### 3. Create Part 1 (first ~8 tests)

Each new file needs:

1. **ADR-009 header comment** (first 3 lines):
   ```mojo
   # ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
   # Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
   # high test load. Split from <original_filename>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
   ```

2. **Updated module docstring** referencing "Part 1 of 2"

3. **All original imports** (copy from original)

4. **The assigned test functions** (full body, no modifications)

5. **Updated `main()`** that only calls the tests in this file, with updated count in final print

### 4. Create Part 2 (remaining tests)

Same structure as Part 1 but with the remaining tests and "Part 2 of 2" labels.

### 5. Delete the original file

```bash
rm tests/path/to/test_original.mojo
```

### 6. Update any `__init__.mojo` or registry files

- Search for references to the original filename
- Update doc comments and any registry lists

```bash
grep -r "test_original" tests/  # find references
```

### 7. Check CI workflow patterns

```bash
grep -A3 "Integration Tests\|<test-group-name>" .github/workflows/comprehensive-tests.yml
```

- If the group uses `pattern: "test_*.mojo"` → **no changes needed**, glob auto-discovers new files
- If the group lists filenames explicitly → update the pattern to include both new files

### 8. Stage, commit, push, PR

```bash
git add tests/path/to/test_original_part1.mojo \
        tests/path/to/test_original_part2.mojo \
        tests/path/to/original.mojo \          # deleted
        tests/path/to/__init__.mojo             # if updated

git commit -m "fix(ci): split test_<name>.mojo into 2 files (ADR-009)"
git push -u origin <branch>
gh pr create ...
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Reducing test count | Deleting some test functions | Violates acceptance criteria — all tests must be preserved | Always split, never delete tests |
| Modifying CI workflow | Adding explicit filenames to pattern | Unnecessary — glob `test_*.mojo` auto-discovers new files | Check the existing pattern before editing workflow |
| Creating 3 files | Splitting 13 tests into 3 files of ~4 each | Over-engineering for a 13-test file | Use 2 files targeting ≤8 each; ADR-009 limit is 10, not 4 |

## Results & Parameters

### ADR-009 Header Template

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <ORIGINAL_FILE>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

### Target Test Distribution

| Scenario | Part 1 | Part 2 | Part 3 |
|----------|--------|--------|--------|
| 11-16 tests | ≤8 | remaining | — |
| 17-24 tests | ≤8 | ≤8 | remaining |

### Key Observations

- CI group using `test_*.mojo` glob: **zero workflow changes needed**
- Pre-commit hooks (mojo format, validate_test_coverage) pass automatically on split files
- `__init__.mojo` doc comments should be updated but are non-functional
- The split is purely mechanical — copy test functions verbatim, no logic changes
