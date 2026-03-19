---
name: adr009-mojo-test-file-split
description: "Split oversized Mojo test files to comply with ADR-009 heap-corruption\
  \ workaround (\u226410 fn test_ per file). Use when: a .mojo test file exceeds 10\
  \ fn test_ functions causing intermittent CI crashes."
category: ci-cd
date: 2026-03-08
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo v0.26.1 causes heap corruption (`libKGENCompilerRTShared.so` JIT fault) under high test load |
| **Symptom** | Intermittent CI crashes in a test group, non-deterministic failures across runs |
| **Root Cause** | Single `.mojo` test file containing >10 `fn test_` functions |
| **Fix** | Split file into multiple files of ≤8 tests each, add ADR-009 header comment |
| **Precedent** | ADR-009 (`docs/adr/ADR-009-heap-corruption-workaround.md`) |

## When to Use

- A `.mojo` test file has more than 10 `fn test_` functions
- CI shows intermittent `libKGENCompilerRTShared.so` crashes in a test group
- ADR-009 compliance audit flags a file as over the limit
- Issue title contains "ADR-009" and involves splitting a test file

## Verified Workflow

### 1. Count fn test_ functions in the target file

```bash
grep -c "^fn test_" tests/path/to/test_file.mojo
```

### 2. Read the original file to plan the split

Split logically by test category (e.g., rotation tests in part1, flip tests in part2).
Target ≤8 tests per file (leaving headroom below the 10-function limit).

### 3. Create part1 and part2 files

Each file must:

- Use the **same imports** as the original
- Include the **ADR-009 header comment** in the module docstring:

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_filename>. See docs/adr/ADR-009-heap-corruption-workaround.md
```

- Have its own `fn main() raises:` that calls only its subset of tests
- Update the final print to reflect the correct count (e.g., "All 7 augmentation tests (part 1) passed!")

### 4. Delete the original file

```bash
rm tests/path/to/test_file.mojo
```

### 5. Verify CI workflow picks up new files automatically

Check that the CI workflow uses a glob pattern (e.g., `transforms/test_*.mojo`) rather than
listing filenames explicitly. If it lists filenames explicitly, update the pattern list.

```bash
grep -n "test_augmentations\|test_<filename>" .github/workflows/comprehensive-tests.yml
```

### 6. Check validate_test_coverage.py for explicit references

```bash
grep -n "<original_filename>" scripts/validate_test_coverage.py
```

If found, update the references to the two new filenames.

### 7. Stage, commit, and verify pre-commit passes

```bash
git add tests/path/to/test_file_part1.mojo tests/path/to/test_file_part2.mojo tests/path/to/test_file.mojo
git commit -m "fix(ci): split <filename> into 2 files (ADR-009)"
```

Pre-commit hooks that run: `mojo format`, `Validate Test Coverage`, `trailing-whitespace`,
`end-of-file-fixer`.

## Results & Parameters

### Split ratio

For a 14-test file: split 7+7 (equal halves). For a 12-test file: split 6+6 or 7+5.
Always target ≤8 per file to leave headroom.

### Naming convention

```text
test_<topic>.mojo          → original (DELETE)
test_<topic>_part1.mojo   → first split file
test_<topic>_part2.mojo   → second split file
```

### ADR-009 header template

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

### CI workflow check

The `Data` test group and most others use glob patterns like `transforms/test_*.mojo`,
so new `_part1`/`_part2` files are discovered automatically without workflow changes.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Checking for explicit filename in CI workflow | Searched for `augmentation` in comprehensive-tests.yml | No explicit references found — glob pattern used instead | Always check CI workflow first; glob patterns auto-discover split files |
| Modifying validate_test_coverage.py | Searched for explicit references to the original filename | No references found — script uses dynamic discovery | validate_test_coverage.py may not need updates if it uses glob/dynamic discovery |
