---
name: mojo-adr009-test-splitting
description: "Use when: (1) a Mojo test file has >10 fn test_ functions and CI shows intermittent libKGENCompilerRTShared.so heap corruption crashes, (2) ADR-009 compliance check fails in PR review, (3) a CI group is flaky with non-deterministic failures under high load, (4) implementing ADR-009 heap corruption workaround"
category: architecture
date: 2026-03-29
version: "2.0.0"
user-invocable: false
verification: unverified
tags: []
---

# Mojo ADR-009 Test Splitting

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-29 |
| Objective | Consolidated workflow for splitting Mojo test files exceeding the ADR-009 ≤10 fn test_ limit to eliminate heap corruption CI failures |
| Outcome | Merged from 3 skills covering basic file split, test file split with glob vs explicit CI patterns, and comprehensive lessons from 10+ split sessions |
| Verification | unverified |

## When to Use

- A Mojo test file has more than 10 `fn test_` functions
- CI fails intermittently with `libKGENCompilerRTShared.so` JIT fault errors
- Failure pattern is non-deterministic (passes sometimes, fails sometimes on same commit)
- A CI group has `continue-on-error: true` due to heap corruption workaround
- ADR-009 compliance check fails in PR review

## Verified Workflow

### Quick Reference

```bash
# 1. Count tests accurately (avoid matching ADR-009 header comment lines)
grep -c "^fn test_[a-z]" tests/path/to/test_file.mojo

# 2. Plan split: parts = ceil(total / 8); target ≤8 per file (not ≤10)
# Formula: parts = ceil(total_tests / 8)

# 3. Verify CI workflow pattern type (glob vs explicit)
grep "test_<name>" .github/workflows/comprehensive-tests.yml
# If glob (test_*.mojo) → new _part files auto-discovered, NO yaml edit needed
# If explicit → must add new filenames to the pattern

# 4. After creating split files, verify test counts
for f in tests/path/test_*_part*.mojo; do
    echo "$f: $(grep -c '^fn test_[a-z]' "$f") tests"
done

# 5. Verify total count matches original
grep -c "^fn test_[a-z]" original.mojo   # e.g. 22
grep -c "^fn test_[a-z]" original_part*.mojo   # should also total 22

# 6. Delete original
git rm tests/path/to/test_original.mojo

# 7. Run pre-commit (validate_test_coverage.py is the safety net)
just pre-commit-all
```

### Step 1: Count Tests Accurately

**CRITICAL**: Use `[a-z]` suffix to avoid matching ADR-009 header comment lines:

```bash
grep -c "^fn test_[a-z]" tests/path/to/test_file.mojo
```

**Never trust the issue description's test count** — issues regularly undercount (e.g., issue said 15, actual was 20). Always grep directly.

If count > 10, proceed with split. Target ≤8 per file for safety margin.

### Step 2: Plan the Split

Use the split sizing formula:
```
parts = ceil(total_tests / 8)
tests_per_part = ceil(total_tests / parts)
```

Examples:
- 22 tests → `ceil(22/8) = 3` parts, with 8/8/6 distribution
- 28 tests → 4 parts × 7 tests each
- 18 tests → 3 parts × 6 tests each (equal thirds)

**Group tests by operation type** for semantic coherence, not arbitrary index slicing. Examples:
- Normalization: forward tests / backward tests / gradient checks
- Conv: initialization+shape / numerical correctness / backward pass
- Loss: forward pass / backward gradients / gradient check

### Step 3: Create Each Split File with ADR-009 Header

Each new file MUST begin with the ADR-009 comment block (NOT a docstring note):

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_file>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

Then include:
- Only the imports needed for that file's tests (prune unused imports; copy full block, then trim)
- The relevant `fn test_` functions verbatim
- A `fn main()` runner calling only those tests

```mojo
fn run_all_tests() raises:
    """Run all <description> tests (Part N)."""
    print("=" * 60)
    print("Test Suite - Part N (Description)")
    print("=" * 60)
    test_function_1()
    test_function_2()
    print("=" * 60)
    print("All Part N tests passed!")
    print("=" * 60)

fn main() raises:
    """Entry point for tests (Part N)."""
    run_all_tests()
```

### Step 4: Determine CI Workflow Update Needs

**Check the existing CI pattern before editing**:

```bash
grep "test_<name>" .github/workflows/comprehensive-tests.yml
```

**Case A: Glob pattern** (e.g., `autograd/test_*.mojo`)
- New `_part1/2/3` files are automatically picked up
- NO workflow YAML changes needed
- `validate_test_coverage.py` uses glob patterns, so no script changes needed either

**Case B: Explicit filename pattern** (e.g., `"core/test_foo.mojo"`)
- MUST update the YAML manually
- Replace the old filename with space-separated new filenames:

```yaml
# Before:
pattern: "core/test_comparison_ops.mojo"

# After:
pattern: "core/test_comparison_ops_part1.mojo test_comparison_ops_part2.mojo test_comparison_ops_part3.mojo"
```

- Remove `continue-on-error: true` if it was added as a heap corruption workaround

### Step 5: Delete the Original File

```bash
git rm tests/path/to/test_original.mojo
```

If you encounter a `.DEPRECATED` artifact from a prior incomplete split:
- Verify split files contain ALL tests from the deprecated file (compare `fn test_` lists)
- Delete the `.DEPRECATED` file with `git rm`

### Step 6: Verify and Commit

```bash
# Verify no file exceeds 8 tests
grep -c "^fn test_[a-z]" tests/path/test_*_part*.mojo

# Run pre-commit — validate_test_coverage.py will fail if new files
# are not referenced in CI (the safety net)
just pre-commit-all

git add tests/path/test_*_part*.mojo .github/workflows/comprehensive-tests.yml
git commit -m "fix(ci): split test_X.mojo into N files per ADR-009"
gh pr create --title "fix(ci): split <file> (<N> tests) per ADR-009" --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Ignoring the ADR-009 limit | Running 22 tests in one file | 13/20 CI runs failing with heap corruption | ADR-009 limit is real — enforce it |
| `continue-on-error: true` | Marking CI group as non-blocking | Masks real failures, doesn't fix root cause | Only use as temporary mitigation, not fix |
| Keeping exactly 10 tests per file | Setting at the ADR-009 hard limit | Edge cases could still trigger corruption | Use ≤8 (70-80% of limit) for a safety margin |
| Trusting issue description test count | Issue #3477 said 15 tests; planned 2-way split | Actual count was 20; 2-way split would yield 10/10, hitting the limit | Always grep `^fn test_[a-z]` to get real count before planning |
| `grep -c "fn test_"` for counting | Counted lines matching pattern | ADR-009 header comment contains "fn test_" text, inflating count by 1 | Use `grep -c "^fn test_[a-z]"` for accurate count |
| Wrong ADR-009 header format | Used docstring note: "Note: Split from..." | ADR-009 requires `# ADR-009:` comment block, not a docstring note | Header must be `#` comment lines at file top, before module docstring |
| Modifying CI workflow glob unnecessarily | Thought new files would not match existing glob | Glob `test_*.mojo` already covers `test_*_part1.mojo` | Verify existing glob before making workflow changes |
| Assuming split completeness from file existence | Saw N split files and `.DEPRECATED`, assumed done | Tests were missing from split files — categories of tests omitted | Always verify by comparing `fn test_` lists between original and split files |
| Splitting imports per-test | Trying to import only what each test needs individually | Added complexity; Mojo imports are file-scoped | Copy full import block, trim unused — simpler |
| Reducing test complexity instead of splitting | Simplifying individual tests to reduce load | Heap corruption is load-based (total `fn test_` count), not complexity-based | Total function count is the trigger, not test logic |

## Results & Parameters

### ADR-009 Limits

| Parameter | Value |
|-----------|-------|
| ADR-009 hard limit | ≤10 `fn test_` per file |
| Target per file | ≤8 (safety margin) |
| Header format | `# ADR-009:` comment block, NOT docstring note |
| Header location | Line 1-4 of file, BEFORE module docstring |
| Imports | Copy full block, trim to only what each part uses |
| `fn main()` | Required in every split file |

### Split Distribution Examples (from sessions)

| Original File | Tests | Parts | Distribution |
|---------------|-------|-------|-------------|
| test_losses.mojo | 28 | 4 | 7/7/7/7 |
| test_reduction.mojo | 22 | 3 | 8/8/6 |
| test_backward.mojo | 21 | 3 | 4/9/8 |
| test_normalization.mojo | 21 | 3 | 8/8/5 |
| test_conv.mojo | 20 | 3 | 7/7/6 |
| test_optimizer_base.mojo | 18 | 3 | 6/6/6 |
| test_comparison_ops.mojo | 19 | 3 | 6/6/7 |

### CI Pattern Verification Checklist

```bash
# 1. Check what type of CI pattern exists for this test
grep "test_<name>" .github/workflows/comprehensive-tests.yml

# 2. If explicit list: update the YAML; if glob: skip YAML edit

# 3. Verify validate_test_coverage.py (uses globs, rarely needs changes)
grep "test_<name>" scripts/validate_test_coverage.py

# 4. Pre-commit validate_test_coverage.py hook is the safety net
# It will fail if new files are not referenced in CI
```
