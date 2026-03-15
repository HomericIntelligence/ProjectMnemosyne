---
name: adr009-split-audit
description: "Audit ADR-009 test file splits to verify no tests were silently dropped. Use when: (1) investigating whether a test file split omitted any test functions, (2) auditing test coverage after ADR-009 heap-corruption workaround splits, (3) verifying that all tests from a deprecated file are present in successor split files."
category: testing
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | ADR-009 requires splitting large Mojo test files to avoid heap corruption, but the split process can silently drop tests if the splitter is not careful about completeness |
| **Solution** | Compare `fn test_` function lists between `.DEPRECATED` source files (or git history) and the union of all active split files to find gaps |
| **Scope** | Any test directory with `.DEPRECATED` files or git-deleted large test files |
| **Risk** | High — dropped gradient/backward tests give false confidence that ML correctness is validated when it isn't |

## When to Use

- After any ADR-009 test file split to verify completeness
- When investigating a CI failure that references a test that "should exist"
- After restoring from git history and finding fewer tests than expected
- Periodically as a health check on the test split inventory
- When opening a follow-up issue from a split PR (e.g., #3444 → #4241)

## Verified Workflow

### Quick Reference

```bash
# 1. Find all deprecated files
find tests/ -name "*.DEPRECATED"

# 2. For each deprecated file, extract test names
grep "^fn test_" <file>.DEPRECATED | sed 's/fn //; s/(.*$//' | sort > /tmp/dep.txt

# 3. Extract all test names from active split files
grep -h "^fn test_" tests/shared/core/test_<prefix>*.mojo | sed 's/fn //; s/(.*$//' | sort > /tmp/split.txt

# 4. Find missing tests
comm -23 /tmp/dep.txt /tmp/split.txt

# 5. For files without .DEPRECATED (deleted in git), recover from history
git log --oneline --diff-filter=D -- "tests/**/<file>.mojo"
git show <parent-commit>^:<path>/<file>.mojo | grep "^fn test_"
```

### Step 1 — Inventory all deprecated/deleted source files

Find both `.DEPRECATED` marker files still present in the repo AND files deleted in ADR-009 split commits:

```bash
# Files still present with .DEPRECATED marker
find tests/ -name "*.DEPRECATED"

# Files deleted in git (no .DEPRECATED marker left)
git log --oneline --all --diff-filter=D -- "tests/shared/core/test_*.mojo" | grep "split\|ADR-009\|heap"
```

### Step 2 — Build test name sets for each deprecated source

For each source file, extract the canonical test function names:

```bash
# From .DEPRECATED file
grep "^fn test_" tests/shared/core/test_foo.mojo.DEPRECATED \
  | sed 's/fn //; s/(.*$//' | sort > /tmp/orig.txt

# From git history (when no .DEPRECATED file)
git show <commit>^:tests/shared/core/test_foo.mojo \
  | grep "^fn test_" | sed 's/fn //; s/(.*$//' | sort > /tmp/orig.txt
```

### Step 3 — Build union of all active split files

Collect test names from every split file that covers the same functionality:

```bash
grep -h "^fn test_" tests/shared/core/test_foo_*.mojo \
  | sed 's/fn //; s/(.*$//' | sort > /tmp/split.txt
```

**Note**: The split files may have MORE tests than the deprecated file (tests added in subsequent commits). The audit only looks for tests that exist in deprecated but NOT in split files.

### Step 4 — Compute the gap

```bash
# Tests in deprecated but NOT in any split file
comm -23 /tmp/orig.txt /tmp/split.txt
```

If empty: all tests preserved. If non-empty: each line is a dropped test.

### Step 5 — Locate implementation in deprecated file

For each dropped test, find its implementation:

```bash
grep -n "fn test_missing_test_name" tests/shared/core/test_foo.mojo.DEPRECATED
# Note the line number, then read the function body
```

### Step 6 — Choose target split file

Apply ADR-009 constraints:
- Each file must have ≤10 `fn test_` functions (target ≤8 for safety buffer)
- Group related tests (e.g., conv tests → conv file, loss tests → loss file)
- Count current tests: `grep -c "^fn test_" <target_file>.mojo`

### Step 7 — Add missing tests

Copy the function body from the deprecated file into the appropriate split file.
Also add the call to `main()`. Verify count stays ≤10 after addition.

### Step 8 — Final verification

```bash
# Confirm per-file counts
grep -c "^fn test_[a-z]" tests/shared/core/test_*.mojo | grep -v ".DEPRECATED"

# Re-run the gap check (should show 0 missing)
grep "^fn test_" tests/shared/core/test_foo.mojo.DEPRECATED \
  | sed 's/fn //; s/(.*$//' | sort > /tmp/orig2.txt
grep -h "^fn test_" tests/shared/core/test_foo_*.mojo \
  | sed 's/fn //; s/(.*$//' | sort > /tmp/split2.txt
comm -23 /tmp/orig2.txt /tmp/split2.txt  # Should be empty
```

## Key Patterns

### Pattern: False completion in commit messages

Split commit messages often say "All N tests preserved" even when they aren't. The commit author
counted tests in the new split files but may have missed gradient tests that require more
complex setup. Always verify with `comm -23` rather than trusting commit messages.

### Pattern: Tests present under different names

`test_operators_preserve_shape` (in `test_extensor_abs_ops.mojo`) and
`test_unary_ops_preserve_shape` (in deprecated) are different tests despite similar intent.
The comm-based diff catches this correctly — a name change is not the same as preservation.

### Pattern: Split files may exceed deprecated count

Later commits often add new tests to split files. This is expected and correct. The audit
only checks for tests that exist in deprecated but not in any split file — the reverse
(new tests in splits not in deprecated) is fine.

### Pattern: Wildcard CI patterns absorb new split files

CI workflows using `test_extensor_*.mojo` wildcards automatically pick up new split files.
Only workflows with explicit filename lists (like the "Core Gradient" group) need updating
when a new split file is added.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trusted commit message | Assumed "All 21 tests preserved" in split commit message was accurate | Commit message was aspirational; actual audit found 1 dropped test in extensor splits | Always verify with `comm -23` diff, never trust commit message counts |
| Searched only .DEPRECATED files | Looked only for `.DEPRECATED` marker files to find deprecated sources | `test_backward.mojo` was deleted entirely (no `.DEPRECATED` left); required `git log --diff-filter=D` | Check both `.DEPRECATED` files AND git-deleted files |
| Checking files individually | Manually read each split file looking for missing tests | Error-prone, slow, easy to miss tests with similar names | Use `comm -23` set difference for reliable gap detection |
| Assuming plan was current | Issue plan said 10 tests were missing; checked those first | Earlier PRs (#127d8e02, d1420696) had already restored the backward and gradient_checking tests | Always re-audit current state from source; plan may be stale |

## Results & Parameters

### Audit of ProjectOdyssey ADR-009 splits (2026-03-15)

| Deprecated File | Deprecated Count | Split Count | Missing |
|---|---|---|---|
| `test_backward.mojo` (git history) | 21 | 23 (+2 new) | **0** |
| `test_gradient_checking.mojo.DEPRECATED` | 16 | 19 (+3 new) | **0** |
| `test_gradient_validation.mojo.DEPRECATED` | 12 | 12 | **0** |
| `test_extensor_new_methods.mojo.DEPRECATED` | 15 | 15 | **0** |
| `test_extensor_operators.mojo.DEPRECATED` | 21 | 21 | **0** |
| `test_extensor_unary_ops.mojo.DEPRECATED` | 7 | 6→**7** | **1 fixed** |

**Fix applied**: Added `test_unary_ops_preserve_shape` to `test_extensor_neg_pos.mojo`
(5 → 6 tests). PR: HomericIntelligence/ProjectOdyssey#4877

### ADR-009 limits

- Hard limit: ≤10 `fn test_` per file
- Target: ≤8 for safety buffer
- Recovery test always fits if deprecated file had ≤10 tests total

### Detection command (copy-paste)

```bash
for deprecated in tests/shared/core/*.DEPRECATED; do
    echo "=== $deprecated ==="
    grep "^fn test_" "$deprecated" | sed 's/fn //; s/(.*$//' | sort > /tmp/dep_tests.txt
    grep -h "^fn test_" tests/shared/core/*.mojo 2>/dev/null \
        | sed 's/fn //; s/(.*$//' | sort > /tmp/split_tests.txt
    missing=$(comm -23 /tmp/dep_tests.txt /tmp/split_tests.txt)
    if [ -z "$missing" ]; then
        echo "✓ All tests preserved"
    else
        echo "✗ MISSING: $missing"
    fi
done
```
