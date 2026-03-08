---
name: adr009-split-audit-and-recovery
description: "Audit completed ADR-009 test file splits for dropped tests, missing headers, and secondary violations. Use when: a split was previously done but tests are still failing or the issue remains open, the post-split test count doesn't match the original file's count, or other test files in the same CI group also violate ADR-009."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | Prior ADR-009 split may drop tests, use wrong header format, or leave other violations in the same CI group |
| **Risk** | Test coverage gaps from dropped tests; secondary heap corruption from un-split files |
| **Trigger** | Issue still open after split, test count mismatch, CI group still flaky |
| **Validated On** | `test_gradient_checking.mojo` (16 → 13 tests in split; 3 dropped; `test_gradient_validation.mojo` also violated) |

## When to Use

- A split was completed (`.DEPRECATED` file exists, new files reference CI workflow), but the issue is still open
- The sum of `fn test_` counts in split files is less than the original file's count
- Other test files referenced in the same CI group also exceed 10 `fn test_` functions
- Split files are missing the required ADR-009 header comment block

## Verified Workflow

### Step 1: Confirm the prior split state

```bash
# Check if DEPRECATED file exists (split was done)
ls tests/**/*.DEPRECATED

# Count tests in all split files vs original deleted file
grep -c "^fn test_" tests/path/to/test_file_part*.mojo

# Check git log for the split commit
git log --oneline -- "tests/path/to/test_file.mojo" | head -5
```

### Step 2: Count original tests from git history

The original file was deleted in the split commit. Recover the count via `git show`:

```bash
# Find the commit that deleted the original
SPLIT_COMMIT=$(git log --oneline -- "tests/path/to/test_original.mojo" | head -1 | cut -d' ' -f1)

# Count original fn test_ functions
git show $SPLIT_COMMIT -- "tests/path/to/test_original.mojo" | grep "^-fn test_" | wc -l

# List original test names
git show $SPLIT_COMMIT -- "tests/path/to/test_original.mojo" | grep "^-fn test_"
```

### Step 3: Identify dropped tests

Compare original test names against what's in the split files:

```bash
# Get all test names from split files
grep "^fn test_" tests/path/to/test_file_*.mojo

# Visually diff original list vs split list to find missing tests
```

### Step 4: Recover dropped tests from git history

Get the full implementation of each missing test:

```bash
git show $SPLIT_COMMIT -- "tests/path/to/test_original.mojo" | grep -A 40 "^-fn test_missing_test_name"
```

Strip the leading `-` from each line (it's the diff prefix) and add to the appropriate split file.

### Step 5: Audit the CI group for secondary violations

Other files in the same CI group may also violate ADR-009:

```bash
# Get CI group pattern from workflow
grep -A 3 '"Core Gradient"' .github/workflows/comprehensive-tests.yml

# Count tests in every file referenced by the group
for f in <files from pattern>; do
  COUNT=$(grep -c "^fn test_" tests/path/to/$f 2>/dev/null || echo 0)
  echo "$COUNT $f"
done | sort -n
```

Any file with > 10 tests must be split. Files with 11-12 tests often went unnoticed.

### Step 6: Verify ADR-009 header format in all split files

The required header is:

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_file>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

Check if existing split files have it:

```bash
grep "^# ADR-009" tests/path/to/test_file_*.mojo
```

If missing (files may have prose docstrings instead), prepend the exact comment block before the docstring.

### Step 7: Split any secondary violations

For each file with > 10 tests, apply the standard split workflow:

- Group tests semantically (e.g., activation functions vs layers)
- Target ≤8 tests per file (ADR-009 hard limit is 10, target 8 for safety margin)
- Rename original to `.DEPRECATED`
- Create split files with ADR-009 header
- Update CI workflow pattern

### Step 8: Update CI workflow

Replace the old filenames with new split filenames:

```yaml
# Before
pattern: "... test_gradient_validation.mojo ..."

# After
pattern: "... test_gradient_validation_activations.mojo test_gradient_validation_layers.mojo ..."
```

### Step 9: Pre-commit and commit

```bash
git add <all modified files>
pixi run pre-commit run --files <files>
git commit -m "fix(ci): restore N missing tests and split secondary violations (ADR-009)

Closes #<issue>
..."
```

## Results & Parameters

From the `test_gradient_checking.mojo` session (2026-03-07):

| Metric | Value |
|--------|-------|
| Original test count | 16 |
| Tests in initial split | 13 (3 dropped) |
| Dropped test names | `test_relu_mixed_inputs`, `test_conv2d_gradient_fp16`, `test_cross_entropy_gradient_fp16` |
| Secondary violation | `test_gradient_validation.mojo` — 12 tests (found via CI group audit) |
| Final split result | 4 files: 9, 7, 8, 4 tests |
| ADR-009 header format | Must use `# ADR-009:` comment (not prose docstring) |

## Key Invariants

- **Always audit secondary files** in the same CI group — they often have violations too
- **Always verify test counts** from git history before closing an issue
- **Dropped tests are silent** — no compiler or CI error warns you; only manual count comparison reveals them
- **Header format matters** — prose docstrings mentioning ADR-009 are NOT equivalent to the required comment block

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assumed split was complete | Checked only that the original file was deleted and new files existed in CI workflow | 3 tests were silently dropped; count 13 ≠ 16 | Always compare `git show <split_commit> \| grep "^-fn test_"` count vs split file count |
| Checked only the primary file | Audited `test_gradient_checking.mojo` split files only | `test_gradient_validation.mojo` (12 tests, same CI group) was still violating ADR-009 | Always audit ALL files referenced in the CI group pattern, not just the issue's primary file |
| Prose docstring as ADR-009 header | Initial splits used `"Note: Split from X due to ADR-009"` in docstring | Issue spec requires exact `# ADR-009:` comment block format | Check issue acceptance criteria for exact header format requirements |
