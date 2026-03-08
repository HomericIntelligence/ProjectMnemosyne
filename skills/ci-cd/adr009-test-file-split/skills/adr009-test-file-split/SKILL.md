---
name: adr009-test-file-split
description: "Split Mojo test files exceeding ADR-009 limit of ≤10 fn test_ functions to prevent heap corruption CI failures. Use when: test file has >10 fn test_ functions, CI shows intermittent libKGENCompilerRTShared.so crashes, or ADR-009 compliance check flags a file."
category: ci-cd
date: 2026-03-08
user-invocable: false
---

## Overview

| Attribute | Value |
|-----------|-------|
| **Trigger** | Mojo test file has >10 `fn test_` functions |
| **Symptom** | Intermittent CI heap corruption: `libKGENCompilerRTShared.so` JIT fault |
| **Fix** | Split into ≤8 tests per file with ADR-009 header comment |
| **CI Impact** | Wildcard patterns auto-discover split files — usually no workflow changes needed |

## When to Use

- A `test_*.mojo` file has **more than 10 `fn test_`** functions (ADR-009 violation)
- CI shows non-deterministic `libKGENCompilerRTShared.so` heap corruption crashes
- Running `grep -c "^fn test_" <file>` returns > 10
- ADR-009 compliance tooling flags a file as over-limit

## Verified Workflow

### 1. Count existing test functions

```bash
grep -c "^fn test_" tests/path/to/test_file.mojo
```

### 2. Plan the split

- Target: ≤8 tests per file (buffer below the 10-function limit)
- Name files `test_<original>_part1.mojo` and `test_<original>_part2.mojo`
- Group logically: basic/correctness in part1, edge cases/special inputs in part2

### 3. Create part1 and part2 files

Each file must include the ADR-009 header comment in the module docstring:

```mojo
"""<Description> (Part N of 2).

ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
high test load. Split from <original_file>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
"""
```

Each file needs its own `fn main() raises:` that calls only its subset of tests.

### 4. Delete the original file

```bash
rm tests/path/to/test_original.mojo
```

### 5. Check CI workflow coverage

Check if the CI group uses a wildcard pattern that will auto-discover the new files:

```bash
grep -A3 "path.*tests/" .github/workflows/comprehensive-tests.yml | grep pattern
```

If the pattern is `test_*.mojo` or `training/test_*.mojo`, the new files are **automatically covered** — no workflow changes needed.

If the original file was listed **explicitly by name**, update the workflow to reference both new filenames.

### 6. Check validate_test_coverage.py

```bash
grep "test_original" scripts/validate_test_coverage.py
```

If the original file was in an exclude list, update it to reference the new filenames (or remove if they should be in CI coverage).

### 7. Commit

```bash
git add tests/path/to/test_original.mojo \
        tests/path/to/test_original_part1.mojo \
        tests/path/to/test_original_part2.mojo
git commit -m "fix(ci): split test_<name>.mojo into 2 files per ADR-009"
```

Pre-commit hooks validate test coverage automatically — they will catch if the split files are not covered.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Keeping original file and adding parts | Rename original to part1, add part2 | Original still has >10 tests; ADR-009 violation remains | Must delete original; only the split files should exist |
| Updating CI workflow explicitly | Editing `comprehensive-tests.yml` to list new filenames | Unnecessary — wildcard `test_*.mojo` patterns auto-discover split files | Check existing CI patterns before editing workflows; wildcards handle discovery |
| Splitting at 5 tests each | Equal distribution regardless of logical grouping | Tests felt arbitrary; harder to understand what each file covers | Group logically: part1=basic/normalization, part2=edge cases/special inputs |

## Results & Parameters

### Key numbers

- ADR-009 limit: **≤10** `fn test_` functions per file
- Recommended target: **≤8** per file (2-function safety buffer)
- Typical split: part1 ≈ 8 tests, part2 ≈ 3 tests

### Verification commands

```bash
# Count tests in each new file
grep -c "^fn test_" tests/path/to/test_original_part1.mojo
grep -c "^fn test_" tests/path/to/test_original_part2.mojo

# Confirm original is gone
ls tests/path/to/test_original.mojo  # Should not exist

# Verify CI discovery (wildcard must match new names)
just test-group tests/path/to "test_*.mojo"
```

### Pre-commit hook output on success

```
Mojo Format..............................................................Passed
Validate Test Coverage...................................................Passed
Trim Trailing Whitespace.................................................Passed
Fix End of Files.........................................................Passed
```

### CI group that uses wildcard pattern (no changes needed)

```yaml
- name: "Misc Tests"
  path: "tests"
  pattern: "test_*.mojo training/test_*.mojo ..."
```
