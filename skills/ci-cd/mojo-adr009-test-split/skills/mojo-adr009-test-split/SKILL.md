---
name: mojo-adr009-test-split
description: "Split oversized Mojo test files to comply with ADR-009 (≤10 fn test_ per file) and eliminate heap corruption CI failures. Use when: a test_*.mojo file exceeds 10 fn test_ functions, CI shows intermittent libKGENCompilerRTShared.so crashes, or a test group non-deterministically fails under high load."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Mojo v0.26.1 heap corruption bug triggers when too many `fn test_` functions are compiled in one file |
| **Limit** | ≤10 `fn test_` per file (ADR-009); target ≤8 for safety margin |
| **Symptom** | `libKGENCompilerRTShared.so` JIT fault — intermittent, load-dependent, not reproducible locally |
| **Fix** | Split the file into N parts, update CI workflow pattern, delete original |
| **Validated On** | `test_reduction.mojo` (22 tests → 3 files of 8/8/6 tests) |

## When to Use

- A `test_*.mojo` file contains more than 10 `fn test_` functions
- CI shows intermittent crashes for a specific test group with no code changes
- Failure pattern is non-deterministic (passes sometimes, fails sometimes on same commit)
- Error log contains `libKGENCompilerRTShared.so` or JIT-related heap fault

## Verified Workflow

### Step 1: Count tests in the offending file

```bash
grep -c "^fn test_" tests/path/to/test_file.mojo
```

If count > 10, proceed. Target ≤8 per output file for safety margin.

### Step 2: Plan the split

Divide tests into logical groups (by operation type, not arbitrarily).
Example: `test_reduction.mojo` (22 tests) → part1 (sum/mean/max/min), part2 (variance/std), part3 (median/percentile).

### Step 3: Create part files with ADR-009 header

Each new file MUST begin with:

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_file>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

Then include:
- Only the imports needed for that file's tests (prune unused imports)
- The relevant `fn test_` functions verbatim
- A `fn main()` runner calling only those tests

### Step 4: Update CI workflow

In `.github/workflows/comprehensive-tests.yml`, find the test group pattern and replace the original filename with all part filenames:

```yaml
# Before:
pattern: "... test_reduction.mojo ..."

# After:
pattern: "... test_reduction_part1.mojo test_reduction_part2.mojo test_reduction_part3.mojo ..."
```

### Step 5: Delete the original file

```bash
rm tests/path/to/test_reduction.mojo
```

### Step 6: Verify with pre-commit

```bash
just pre-commit
```

The `validate_test_coverage.py` hook will confirm no files are uncovered by CI.

### Step 7: Commit and PR

```bash
git add <files>
git commit -m "fix(ci): split <file> (<N> tests) per ADR-009"
gh pr create --title "fix(ci): split <file> (<N> tests) per ADR-009" --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Max tests per file | 10 (ADR-009 limit) |
| Target tests per file | ≤8 (safety margin) |
| Header comment | Required on every split file |
| Imports | Prune to only what each part needs |
| `fn main()` | Required in each part (Mojo test runner entry point) |
| CI pattern field | Space-separated filenames in `comprehensive-tests.yml` |

### Split sizing formula

```
parts = ceil(total_tests / 8)
tests_per_part = ceil(total_tests / parts)
```

For 22 tests: `ceil(22/8) = 3` parts, with 8/8/6 distribution.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Ignoring the limit | Running 22 tests in one file | 13/20 CI runs failing with heap corruption | ADR-009 limit is real — enforce it |
| `continue-on-error: true` | Marking group non-blocking in CI | Hides signal, doesn't fix root cause | Only use as temporary mitigation, not fix |
| Reducing test complexity | Simplifying individual tests | Heap corruption is load-based, not complexity-based | Total `fn test_` count is the trigger, not test logic |
