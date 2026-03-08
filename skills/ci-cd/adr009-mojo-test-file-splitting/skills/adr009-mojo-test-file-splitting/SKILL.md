---
name: adr009-mojo-test-file-splitting
description: "Split Mojo test files exceeding ≤10 fn test_ limit to fix ADR-009 heap corruption in CI. Use when: (1) a Mojo test file has >10 fn test_ functions, (2) CI has intermittent non-deterministic heap crashes, (3) enforcing ADR-009 compliance."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

## Overview

| Attribute | Value |
|-----------|-------|
| **Problem** | Mojo v0.26.1 JIT (`libKGENCompilerRTShared.so`) crashes non-deterministically under high test load when a single file has >10 `fn test_` functions |
| **ADR** | ADR-009 — max ≤10 `fn test_` functions per `.mojo` test file |
| **Fix** | Split oversized test files into `_part1.mojo` / `_part2.mojo` with ≤8 tests each |
| **CI Impact** | Eliminates intermittent CI group failures (observed: 13/20 runs failing) |
| **Scope** | Any `.mojo` test file with >10 `fn test_` functions |

## When to Use

- A Mojo test file contains more than 10 `fn test_` functions
- CI shows intermittent, non-deterministic failures in a test group (not reproducible locally)
- You count `fn test_` in a file and find the number exceeds 10
- Implementing a new test file and anticipating it will grow beyond 10 tests
- ADR-009 compliance audit for the test suite

## Verified Workflow

### Step 1: Count tests in the file

```bash
grep -c "^fn test_" tests/path/to/test_file.mojo
```

If result > 10, the file must be split.

### Step 2: Read and plan the split

Read the full file, then divide `fn test_` functions into two groups of ≤8 each, grouped by logical category (e.g., core behavior, edge cases, tracking).

### Step 3: Create part1 and part2 files

Each new file needs:

1. Updated docstring describing what subset of tests it covers
2. The ADR-009 header comment (mandatory):

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_filename>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

3. All imports from the original file (identical)
4. The subset of `fn test_` functions assigned to this part
5. An updated `fn main()` that only calls the tests in this file

### Step 4: Delete the original file

```bash
rm tests/path/to/test_file.mojo
```

### Step 5: Update validate_test_coverage.py

Replace the single entry in the exclusion list:

```python
# Before
"tests/shared/training/test_file.mojo",

# After
"tests/shared/training/test_file_part1.mojo",
"tests/shared/training/test_file_part2.mojo",
```

### Step 6: Check CI workflow patterns

The CI workflow (`comprehensive-tests.yml`) typically uses glob patterns like `training/test_*.mojo`, so new `_part1` / `_part2` files are picked up automatically. Verify no hardcoded filename references exist:

```bash
grep -r "test_original_name" .github/workflows/
```

### Step 7: Commit and PR

```bash
git add tests/path/to/test_file_part1.mojo \
        tests/path/to/test_file_part2.mojo \
        tests/path/to/test_file.mojo \  # deleted
        scripts/validate_test_coverage.py
git commit -m "fix(ci): split test_file.mojo into two files (ADR-009)"
gh pr create --title "fix(ci): split test_file.mojo to fix ADR-009 heap corruption"
```

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| **Max tests per file** | 10 (ADR-009 hard limit) |
| **Target tests per part** | ≤8 (buffer below limit) |
| **Naming convention** | `test_<name>_part1.mojo`, `test_<name>_part2.mojo` |
| **ADR reference** | `docs/adr/ADR-009-heap-corruption-workaround.md` |
| **Mojo version affected** | v0.26.1 (JIT fault in libKGENCompilerRTShared.so) |
| **CI failure pattern** | Non-deterministic failures, load-dependent, 13/20 observed |

### ADR-009 Header Template (copy-paste)

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

### Files commonly requiring updates

- `scripts/validate_test_coverage.py` — exclusion list uses exact filenames
- `.github/workflows/comprehensive-tests.yml` — check for hardcoded filenames (glob patterns auto-update)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Ignore the limit | Running 16 tests in one file | Non-deterministic heap corruption crashes CI 13/20 runs | Always split at >10; don't wait for failures |
| Reducing test count | Deleting some tests to stay under limit | Loses test coverage | Split into parts, never delete tests |
| Hardcoding filenames in CI workflow | Updating `comprehensive-tests.yml` with explicit part1/part2 filenames | Unnecessary — the workflow uses `test_*.mojo` globs | Check glob patterns first before editing CI workflow |
| Creating backup files | Keeping `.orig` or `.bak` copies of original | Pollutes git staging and can confuse pre-commit hooks | Delete original cleanly; git history preserves it |
