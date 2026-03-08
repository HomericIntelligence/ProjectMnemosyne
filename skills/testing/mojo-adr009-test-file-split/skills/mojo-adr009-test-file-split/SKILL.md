---
name: mojo-adr009-test-file-split
description: "Split Mojo test files exceeding the ADR-009 ≤10 fn test_ limit to prevent libKGENCompilerRTShared.so heap corruption. Use when: a Mojo test file has >10 fn test_ functions and causes non-deterministic CI failures (heap corruption/JIT fault)."
category: testing
date: 2026-03-07
user-invocable: false
---

# Mojo ADR-009: Split Test Files to Prevent Heap Corruption

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-07 |
| **Objective** | Split `test_emnist.mojo` (21 `fn test_` functions) into 3 ADR-009 compliant files |
| **Outcome** | ✅ 21 tests preserved across 3 files; pre-commit passes; PR #4233 created |
| **PR** | HomericIntelligence/ProjectOdyssey#4233 |
| **ADR** | docs/adr/ADR-009-heap-corruption-workaround.md |

Mojo v0.26.1 has a JIT heap corruption bug in `libKGENCompilerRTShared.so` that triggers
when a single test file contains many `fn test_` functions. ADR-009 mandates ≤10 `fn test_`
functions per `.mojo` test file. When a file exceeds this limit, CI for the associated test
group fails non-deterministically.

This skill documents the repeatable workflow for splitting an oversized Mojo test file into
ADR-009 compliant parts, without losing any tests.

## When to Use

- A Mojo test file has >10 `fn test_` functions
- CI shows non-deterministic heap corruption (`libKGENCompilerRTShared.so` JIT fault) for a test group
- ADR-009 compliance review finds a file over the limit
- A new large Mojo test file is being authored and should be pre-split

## Verified Workflow

### Step 1 — Count fn test_ Functions

```bash
grep -c "^fn test_" tests/path/to/test_file.mojo
```

If count > 10, the file must be split. Target ≤8 per file for headroom.

### Step 2 — List All Test Functions in Order

```bash
grep -n "^fn test_" tests/path/to/test_file.mojo
```

Record the function names and their natural groupings (init, access, shape, class counts,
integration, edge cases, performance, etc.).

### Step 3 — Plan the Split

Divide functions into groups of ≤8 tests, grouped by functional area:

| Part | Tests | Functional Area |
|------|-------|----------------|
| `_part1.mojo` | ≤8 | Initialization, basic access |
| `_part2.mojo` | ≤8 | Shape, class counts, integration |
| `_part3.mojo` | ≤5 | Edge cases, performance |

### Step 4 — Create Each Part File

Each part file must include:

1. **Module docstring** naming the part and listing what it covers
2. **ADR-009 header comment** (exact text required):

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_filename>. See docs/adr/ADR-009-heap-corruption-workaround.md
```

3. **All imports** from the original file (copy exactly)
4. **Shared helper functions** (copy to each part that uses them, or import if refactored)
5. **The test functions** for this part
6. **`fn main() raises`** runner calling only this part's tests

### Step 5 — Delete the Original File

```bash
rm tests/path/to/test_file.mojo
```

Do NOT use `git mv` — the original file is replaced by multiple new files, not renamed.

### Step 6 — Verify Test Counts

```bash
grep -c "^fn test_" tests/path/to/test_file_part1.mojo
grep -c "^fn test_" tests/path/to/test_file_part2.mojo
grep -c "^fn test_" tests/path/to/test_file_part3.mojo
```

All must be ≤10. Sum must equal original count.

### Step 7 — Check CI Workflow Coverage

The CI workflow pattern for datasets uses wildcards like `datasets/test_*.mojo`. Verify the
new part files will be discovered automatically:

```bash
grep -A2 "datasets" .github/workflows/comprehensive-tests.yml
```

If the wildcard `test_*.mojo` covers the new `test_*_part1.mojo` files, no workflow update
is needed. If explicit filenames were used, update the pattern list.

### Step 8 — Stage and Commit

```bash
git add tests/path/to/test_file.mojo  # deleted
git add tests/path/to/test_file_part1.mojo
git add tests/path/to/test_file_part2.mojo
git add tests/path/to/test_file_part3.mojo

git commit -m "fix(ci): split <test_file> into N files per ADR-009

<original> had <N> fn test_ functions, exceeding the ADR-009 limit of 10.
Split into <N> files of ≤10 tests each to prevent heap corruption.

Closes #<issue>"
```

### Step 9 — Verify Pre-commit Passes

Pre-commit hooks include `mojo format` and `validate_test_coverage.py`. Both must pass.
`validate_test_coverage.py` checks that all `test_*.mojo` files are covered by CI patterns.
The wildcard `datasets/test_*.mojo` covers part files automatically.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using `git mv` for original file | Renaming original to `_part1.mojo` to preserve history | History on deleted tests in split-out parts is lost anyway; adds confusion | Just delete the original and create new files; history is in git log |
| Updating CI workflow patterns | Explicitly listing `test_emnist_part1.mojo test_emnist_part2.mojo test_emnist_part3.mojo` | Unnecessary — the wildcard `datasets/test_*.mojo` already covers all new files | Always check existing patterns before editing the CI workflow |
| Shared helper functions in separate file | Extracting `create_mock_idx_files` to a shared helper | No shared helper import pattern established for Mojo test files | Copy shared helpers to each part file that uses them |

## Results & Parameters

**Original file**: `tests/shared/data/datasets/test_emnist.mojo` — 21 `fn test_` functions

**Split result**:

| File | fn test_ count | Functional Area |
|------|---------------|----------------|
| `test_emnist_part1.mojo` | 9 | Init + access (getitem, bounds, negative index) |
| `test_emnist_part2.mojo` | 8 | Shape + class counts + integration (get_train/test_data) |
| `test_emnist_part3.mojo` | 4 | Train/test sizes + consistency + valid splits + perf |
| **Total** | **21** | All original tests preserved |

**CI workflow pattern**: `datasets/test_*.mojo` — no workflow update required.

**Pre-commit hooks**: All pass (mojo format, validate test coverage, trailing whitespace,
end-of-file fixer, large file check).

**ADR-009 header** (copy-paste template):

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_filename>. See docs/adr/ADR-009-heap-corruption-workaround.md
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3441, PR #4233 | [notes.md](../references/notes.md) |

## Related Skills

- `split-large-test-file` — Python test splitting due to Edit tool token limits (different problem)
- `mojo-test-runner` — Running Mojo test suites
- `validate-mojo-patterns` — Checking Mojo code against project standards
