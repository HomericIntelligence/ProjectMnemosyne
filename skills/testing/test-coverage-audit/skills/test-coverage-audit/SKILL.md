---
name: test-coverage-audit
description: "Audit existing test files before adding new tests to avoid duplicating coverage. Use when: an issue requests adding tests for a method, investigating whether a test coverage gap is real, or consolidating test suites."
category: testing
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Trigger** | Issue asks to add tests for a method or feature |
| **Risk** | Low — read-only audit before any writes |
| **Payoff** | Avoids wasted effort duplicating existing tests |
| **Language** | Any (Mojo, Python, etc.) |

## When to Use

- Issue says "add test coverage for `__hash__`" (or any method)
- Issue says "add any missing cases" — implies audit first
- You're about to write tests and haven't verified what exists
- Multiple test files exist and coverage may be split across them

## Verified Workflow

### Quick Reference

```bash
# Search all test files for the method name
grep -rn "__hash__\|hash(" tests/ --include="*.mojo" --include="*.py"

# List files that match
grep -rl "__hash__" tests/

# Read matching sections to verify coverage
```

### Step 1: Search for existing tests

Use `Grep` to find all test files containing the method name (case-insensitive):

```
pattern: hash|__hash__
path: tests/
glob: *.mojo  (or *.py)
output_mode: files_with_matches
```

### Step 2: Map issue requirements to tests

For each requirement in the issue, find the corresponding test function:

| Requirement | Search pattern |
|-------------|---------------|
| "identical X produce equal Y" | `test_.*immutable\|test_.*equal\|assert_equal.*hash` |
| "differing by shape" | `test_.*shape` |
| "differing by dtype" | `test_.*dtype` |
| "differing by value" | `test_.*value.*differ\|test_.*different_val` |

### Step 3: Read the test sections

Read the relevant lines around each match to verify the test actually covers the requirement
(not just mentions the keyword).

### Step 4: Build a coverage matrix

| Requirement | Covered? | Test function | File |
|-------------|----------|---------------|------|
| Identical → equal hash | ✅ | `test_hash_immutable` | `test_utility.mojo:672` |
| Different shape → diff hash | ✅ | `test_hash_different_shapes_differ` | `test_utility.mojo:748` |
| Different dtype → diff hash | ✅ | `test_hash_different_dtypes_differ` | `test_utility.mojo:728` |
| Different value → diff hash | ✅ | `test_hash_different_values_differ` | `test_utility.mojo:684` |

### Step 5: Add only what's missing

- If all cases are covered: add a coverage comment mapping requirements to tests,
  then close the issue via PR.
- If cases are missing: write the missing test functions following the existing patterns.

### Step 6: Add coverage comment (when no new tests needed)

Insert a comment block above the test section documenting the coverage mapping:

```mojo
# ============================================================================
# Test __hash__
# Coverage (issue #NNNN):
#   (1) identical tensors produce equal hashes      -> test_hash_immutable
#   (2) different shape produces different hash     -> test_hash_different_shapes_differ
#   (3) different dtype produces different hash     -> test_hash_different_dtypes_differ
#   (4) different element value produces diff hash  -> test_hash_different_values_differ
# ============================================================================
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Writing tests immediately | Started drafting test functions before searching | Would have duplicated 8+ existing tests | Always grep first |
| Single-file search | Only searched `test_utility.mojo` | Missed `test_hash.mojo` with 15 additional NaN-stability tests | Search all files in `tests/` |
| Trusting issue title | Assumed "add tests" meant tests were missing | All 4 required cases already existed in main | Issue wording "add any missing cases" implies audit |

## Results & Parameters

**Session outcome**: Issue #4051 closed with a 6-line coverage comment, no new test functions needed.

**Key metrics**:
- Files searched: 5 (via `grep -rl hash tests/`)
- Existing hash tests found: 23 functions across 2 files
- New tests written: 0
- Coverage comment lines added: 6

**Commit format used**:

```
docs(test): document __hash__ coverage mapping for issue #NNNN

Audit confirmed all four required hash test cases are already present.
Added coverage comment mapping each requirement to its test function.

Closes #NNNN
```
