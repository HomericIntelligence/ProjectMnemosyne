---
name: mojo-adr009-test-split
description: "Split Mojo test files exceeding ADR-009's 10 fn test_ limit to fix intermittent heap corruption CI failures. Use when: a Mojo test file has >10 fn test_ functions, CI shows libKGENCompilerRTShared.so crashes, or ADR-009 compliance is required."
category: ci-cd
date: 2026-03-08
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo v0.26.1 causes heap corruption (libKGENCompilerRTShared.so JIT fault) when a test file contains more than 10 `fn test_` functions |
| **ADR** | ADR-009 — mandates ≤10 `fn test_` functions per file |
| **Fix** | Split offending file into 2+ files of ≤8 tests each, add ADR-009 header, update coverage scripts |
| **CI Impact** | Eliminates non-deterministic CI failures in affected test groups |

## When to Use

- A Mojo test file has more than 10 `fn test_` functions
- CI group fails intermittently with `libKGENCompilerRTShared.so` JIT faults
- Pre-commit `Validate Test Coverage` hook references a file that needs splitting
- ADR-009 compliance review identifies overfull test files

## Verified Workflow

### 1. Count test functions in the offending file

```bash
grep -c "^fn test_" tests/path/to/test_file.mojo
```

### 2. Plan the split (target ≤8 tests per file)

Divide tests into logical groups:
- Part 1: core functionality tests (~8 tests)
- Part 2: edge cases, property tests, accuracy tests (~remaining)

### 3. Create the new files

Each new file must include the ADR-009 header comment at the very top:

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_file>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

Name the files `test_<name>_part1.mojo` and `test_<name>_part2.mojo`.

Each file needs its own `fn main() raises:` that calls only its own tests.

### 4. Delete the original file

```bash
git rm tests/path/to/test_original.mojo
```

### 5. Update validate_test_coverage.py

Replace the single filename entry with the two new filenames in the `exclude_training_patterns` (or equivalent) list:

```python
# Before
"tests/shared/training/test_step_scheduler.mojo",

# After
"tests/shared/training/test_step_scheduler_part1.mojo",
"tests/shared/training/test_step_scheduler_part2.mojo",
```

### 6. Check CI workflow — usually no changes needed

If the CI workflow uses a glob pattern like `training/test_*.mojo`, the new files are automatically picked up. Only update the workflow if it references specific filenames.

### 7. Commit and verify pre-commit passes

```bash
git add tests/path/to/test_<name>_part1.mojo tests/path/to/test_<name>_part2.mojo scripts/validate_test_coverage.py
git commit -m "fix(ci): split test_<name>.mojo to fix ADR-009 heap corruption

Split <N> fn test_ functions into two files of ≤8 tests each.
Closes #<issue>"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Update CI workflow pattern | Modified comprehensive-tests.yml to reference new filenames explicitly | Not needed — glob `training/test_*.mojo` already covers new files | Check the CI pattern before editing the workflow; glob patterns handle splits automatically |
| Keeping original file as wrapper | Considered keeping original and importing from split files | Mojo doesn't support cross-file test imports in this pattern | Delete original entirely; each file is self-contained with its own main() |

## Results & Parameters

**Test distribution that worked (11 → 8 + 3):**
- Part 1: core, gamma factor, step size, and first edge cases (≤8)
- Part 2: remaining edge cases, property tests, formula accuracy (≤3)

**ADR-009 header template (copy-paste):**
```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

**Target per-file test count:** ≤8 (conservative buffer below the 10-limit)

**CI group that was affected:** `Shared Infra & Testing` — pattern `training/test_*.mojo`
