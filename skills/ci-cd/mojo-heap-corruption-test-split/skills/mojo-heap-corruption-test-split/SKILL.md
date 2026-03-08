---
name: mojo-heap-corruption-test-split
description: "Split Mojo test files exceeding ADR-009 limit (10 fn test_ per file) to prevent heap corruption in Mojo v0.26.1. Use when: a .mojo test file has >10 fn test_ functions causing intermittent CI failures."
category: ci-cd
date: 2026-03-08
user-invocable: false
---

## Overview

| Property | Value |
|----------|-------|
| **Problem** | Mojo v0.26.1 has a heap corruption bug (`libKGENCompilerRTShared.so` JIT fault) triggered by high test load — specifically when a single test file contains more than 10 `fn test_` functions |
| **Solution** | Split oversized test files into smaller files of ≤8 tests each, add ADR-009 header comment, ensure CI glob patterns cover new files |
| **ADR** | ADR-009: ≤10 `fn test_` functions per file |
| **Target** | ≤8 tests per file (conservative buffer below the 10-test limit) |
| **CI Impact** | Fixes non-deterministic CI failures (heap corruption triggers under load) |

## When to Use

- A `.mojo` test file has **more than 10 `fn test_` functions**
- CI group fails intermittently with `libKGENCompilerRTShared.so` JIT fault
- Implementing ADR-009 compliance for Mojo v0.26.1
- A new test file is being created that might exceed 10 tests

## Verified Workflow

### Step 1: Count fn test_ functions

```bash
grep -c "^fn test_" tests/path/to/test_file.mojo
```

If count > 10, split is required per ADR-009.

### Step 2: Plan the split

Aim for ≤8 tests per file. Group tests by logical category:

- Part 1: Creation + Randomization + Correctness basics (~8 tests)
- Part 2: Remaining correctness + Replacement + Integration + Performance (~5 tests)

### Step 3: Create split files with ADR-009 header

Each new file must start with the ADR-009 tracking comment in its docstring:

```mojo
"""Tests for <module> (part N of M): <category1>, <category2>.

# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_filename>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
"""
```

### Step 4: Verify test count in each new file

```bash
grep -c "^fn test_" tests/path/to/test_file_part1.mojo
grep -c "^fn test_" tests/path/to/test_file_part2.mojo
# Both must be ≤ 8
```

### Step 5: Delete the original file

```bash
rm tests/path/to/test_original.mojo
```

### Step 6: Check CI workflow coverage

The CI `comprehensive-tests.yml` typically uses glob patterns like `test_*.mojo`. Verify new files are covered:

```bash
# Pattern samplers/test_*.mojo automatically covers test_foo_part1.mojo and test_foo_part2.mojo
grep -A3 "samplers/test_" .github/workflows/comprehensive-tests.yml
```

If the CI uses explicit file lists rather than globs, update the workflow to include the new filenames.

### Step 7: Verify validate_test_coverage.py still passes

```bash
python3 scripts/validate_test_coverage.py
```

The script uses glob expansion — it will automatically find new `test_*_part1.mojo` and `test_*_part2.mojo` files if the CI pattern uses wildcards.

### Step 8: Commit

```bash
git add tests/path/to/test_file_part1.mojo tests/path/to/test_file_part2.mojo tests/path/to/test_original.mojo
git commit -m "fix(ci): split test_foo.mojo into 2 files to fix heap corruption (ADR-009)"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Modifying CI workflow pattern | Considered updating `samplers/test_*.mojo` pattern to explicit filenames | Not needed — glob patterns already cover `test_*_part1.mojo` and `test_*_part2.mojo` | Always check if existing glob patterns already cover new filenames before modifying CI |
| Updating validate_test_coverage.py | Considered adding explicit entries for new files | Not needed — script uses `rglob("test_*.mojo")` which picks up all matching files dynamically | Dynamic glob-based coverage scripts self-update when files are renamed/split |

## Results & Parameters

### ADR-009 Required Header Template

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_file>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

### Naming Convention

| Original | Part 1 | Part 2 |
|----------|--------|--------|
| `test_foo.mojo` | `test_foo_part1.mojo` | `test_foo_part2.mojo` |
| `test_bar_sampler.mojo` | `test_bar_sampler_part1.mojo` | `test_bar_sampler_part2.mojo` |

### Test Distribution Strategy

- **Target**: ≤8 tests per file (buffer below 10-test ADR-009 limit)
- **Group by category**: Keep logically related tests together
- **Part 1**: Usually creation/basic tests
- **Part 2**: Usually integration/edge case/performance tests

### Pre-commit Hook Compatibility

Mojo format pre-commit hook runs on new files automatically. No special configuration needed. The `validate_test_coverage.py` pre-commit hook uses glob patterns and will verify new files are covered by CI.
