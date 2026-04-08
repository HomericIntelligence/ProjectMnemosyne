---
name: adr009-split-audit
description: "Audit ADR-009 test file splits to verify no tests were silently dropped, create GitHub issues for violations, and validate coverage. Use when: (1) verifying that all tests from a deprecated/deleted file are present in successor split files, (2) auditing all test files in a family or CI group for ADR-009 compliance, (3) creating GitHub issues for ADR-009 violating files in bulk, (4) investigating whether a prior split omitted any test functions, (5) running a periodic health check on the split test inventory."
category: testing
date: 2026-04-07
version: "1.1.0"
user-invocable: false
tags: [adr-009, mojo, audit, testing, github-issues, coverage, dropped-tests]
---

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-07 |
| **Objective** | Consolidate all ADR-009 audit knowledge: split completeness verification, codebase-wide violation detection, GitHub issue creation, and CI group family audits |
| **Outcome** | Single skill covering dropped-test detection, git history recovery, bulk issue creation, family-wide audits, and validate_test_coverage.py updates |
| **Risk** | High — dropped gradient/backward tests give false confidence that ML correctness is validated when it isn't |

> **ADR-009 is now OBSOLETE** — the heap corruption bug has been fixed. This skill is preserved for historical reference and for understanding existing split files.

## When to Use

- After any ADR-009 test file split to verify split completeness (no dropped tests)
- When a CI failure references a test that "should exist" but doesn't
- After restoring from git history and finding fewer tests than expected
- Periodically as a health check on the test split inventory
- When auditing all test files in a family/module for compliance before or after fixing one violation
- When creating GitHub issues for all files violating ADR-009 in bulk
- When an issue is still open after a split was supposedly completed

## Verified Workflow

### Quick Reference

```bash
# Find all deprecated files
find tests/ -name "*.DEPRECATED"

# For each deprecated file, detect dropped tests
grep "^fn test_" <file>.DEPRECATED | sed 's/fn //; s/(.*$//' | sort > /tmp/dep.txt
grep -h "^fn test_" tests/shared/core/test_<prefix>*.mojo | sed 's/fn //; s/(.*$//' | sort > /tmp/split.txt
comm -23 /tmp/dep.txt /tmp/split.txt   # empty = all tests preserved

# For files deleted without .DEPRECATED (recover from git)
git log --oneline --diff-filter=D -- "tests/**/<file>.mojo"
git show <parent-commit>^:<path>/<file>.mojo | grep "^fn test_"

# Codebase-wide violation scan
for f in $(find tests -name "test_*.mojo" | sort); do
  count=$(grep -c "^fn test_" "$f" 2>/dev/null || echo "0")
  if [ "$count" -gt 10 ]; then echo "$count $f"; fi
done | sort -rn
```

### Part A: Post-Split Completeness Audit

#### Step 1: Confirm the prior split state

```bash
# Check if .DEPRECATED file exists
ls tests/**/*.DEPRECATED

# Count tests in all split files
grep -c "^fn test_" tests/path/to/test_file_part*.mojo

# Find the split commit in git history
git log --oneline -- "tests/path/to/test_file.mojo" | head -5
```

#### Step 2: Build test name set for the deprecated source

**From a `.DEPRECATED` file still on disk:**
```bash
grep "^fn test_" tests/shared/core/test_foo.mojo.DEPRECATED \
  | sed 's/fn //; s/(.*$//' | sort > /tmp/orig.txt
```

**From git history (when no `.DEPRECATED` file):**
```bash
# Find the commit that deleted the original
SPLIT_COMMIT=$(git log --oneline -- "tests/path/to/test_original.mojo" | head -1 | cut -d' ' -f1)

# Count and list original test names
git show $SPLIT_COMMIT -- "tests/path/to/test_original.mojo" | grep "^-fn test_" | wc -l
git show $SPLIT_COMMIT -- "tests/path/to/test_original.mojo" | grep "^-fn test_" \
  | sed 's/^-fn //; s/(.*$//' | sort > /tmp/orig.txt
```

#### Step 3: Build union of all active split files

```bash
grep -h "^fn test_" tests/shared/core/test_foo_*.mojo \
  | sed 's/fn //; s/(.*$//' | sort > /tmp/split.txt
```

**Note**: Split files may have MORE tests than the deprecated file (tests added in subsequent commits). This is expected and correct. The audit only checks for tests in deprecated that are NOT in any split file.

#### Step 4: Compute the gap

```bash
# Tests in deprecated but NOT in any split file
comm -23 /tmp/orig.txt /tmp/split.txt
```

If empty: all tests preserved. If non-empty: each line is a dropped test.

#### Step 5: Recover dropped tests from git history

```bash
# Get full implementation of a missing test
git show $SPLIT_COMMIT -- "tests/path/to/test_original.mojo" | grep -A 40 "^-fn test_missing_test_name"
```

Strip the leading `-` from each line (it's the diff prefix) and add to the appropriate split file. Also add the call to `main()`. Verify count stays <=10 after addition.

#### Step 6: Verify ADR-009 header format in all split files

The required header is a comment block placed BEFORE the docstring:

```mojo
# ADR-009: This file is intentionally limited to <=10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_file>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

Check existing files:
```bash
grep "^# ADR-009" tests/path/to/test_file_*.mojo
```

Prose docstrings mentioning ADR-009 are NOT equivalent to the required comment block.

#### Step 7: Final verification

```bash
# Confirm per-file counts
grep -c "^fn test_[a-z]" tests/shared/core/test_*.mojo | grep -v ".DEPRECATED"

# Re-run the gap check (should show empty)
comm -23 /tmp/orig.txt /tmp/split.txt
```

#### Batch audit across all deprecated files

```bash
for deprecated in tests/shared/core/*.DEPRECATED; do
    echo "=== $deprecated ==="
    grep "^fn test_" "$deprecated" | sed 's/fn //; s/(.*$//' | sort > /tmp/dep_tests.txt
    grep -h "^fn test_" tests/shared/core/*.mojo 2>/dev/null \
        | sed 's/fn //; s/(.*$//' | sort > /tmp/split_tests.txt
    missing=$(comm -23 /tmp/dep_tests.txt /tmp/split_tests.txt)
    if [ -z "$missing" ]; then
        echo "  All tests preserved"
    else
        echo "  MISSING: $missing"
    fi
done
```

### Part B: Family/CI-Group Compliance Audit

When fixing one ADR-009 file in a family, always audit ALL sibling files.

#### Step 1: Audit the entire file family

```bash
for f in tests/shared/core/test_<family>_*.mojo; do
  count=$(grep -c "^fn test_" "$f" 2>/dev/null || echo 0)
  echo "$f: $count tests"
done
```

Identify every file where count > 10. Fix ALL of them in one PR.

#### Step 2: Audit the full CI group

```bash
# Get CI group pattern
grep -A 3 '"Core Gradient"' .github/workflows/comprehensive-tests.yml

# Count tests in every file in the group
for f in <files from pattern>; do
  COUNT=$(grep -c "^fn test_" tests/path/to/$f 2>/dev/null || echo 0)
  echo "$COUNT $f"
done | sort -n
```

Any file with > 10 tests must be split. Files with 11-12 tests often go unnoticed.

#### Step 3: Check if the issue-specified file has already been fixed

```bash
git log --all --oneline -- "tests/path/to/test_file.mojo" | head -5
```

If a prior commit already split the file, a `.DEPRECATED` marker may exist. Skip re-splitting already-done files.

### Part C: Codebase-Wide Violation Scan and Issue Creation

#### Step 1: Count all violations

```bash
for f in $(find tests -name "test_*.mojo" | sort); do
  count=$(grep -c "^fn test_" "$f" 2>/dev/null || echo "0")
  if [ "$count" -gt 10 ]; then echo "$count $f"; fi
done | sort -rn
```

#### Step 2: Map files to CI groups

Read `.github/workflows/comprehensive-tests.yml` to determine which CI job runs each file. Record: CI group name, sample failing run IDs.

#### Step 3: Check for existing issues (avoid duplicates)

```bash
gh issue list --label "ci-cd" --search "ADR-009" --state open --limit 200 --json number,title
```

#### Step 4: Synchronous batch creation script

```python
import subprocess, math

VIOLATING_FILES = [
    # (file_path, test_count, ci_group, [sample_run_ids])
    ("tests/shared/core/test_matrix.mojo", 64, "Core Tensors", ["22750802815"]),
    # ... ordered by test_count descending
]

def compute_split(test_count):
    """Split into files of <=8 tests (buffer below 10-test limit)."""
    return math.ceil(test_count / 8)

def create_issue(file_path, test_count, ci_group, run_ids):
    filename = file_path.split("/")[-1]
    num_files = compute_split(test_count)
    base = filename.replace(".mojo", "").replace("test_", "")
    title = f"fix(ci): split {filename} ({test_count} tests) — Mojo heap corruption (ADR-009)"
    body = f"""## Problem

`{file_path}` contains **{test_count} `fn test_` functions**, exceeding the ADR-009 limit of 10 per file.

This causes intermittent heap corruption crashes in Mojo v0.26.1 (`libKGENCompilerRTShared.so`
JIT fault), making the **{ci_group}** CI group non-deterministically fail.

## Evidence

- **File**: `{file_path}`
- **Test count**: {test_count} (limit: 10, target after split: <=8)
- **CI Group**: `{ci_group}`
- **Sample failing run IDs**: {run_ids}

Related: #2942, ADR-009 (`docs/adr/ADR-009-heap-corruption-workaround.md`)

## Fix

Split `{file_path}` into **{num_files} files** of <=8 tests each.

Each split file must include the ADR-009 header comment:
```mojo
# ADR-009: This file is intentionally limited to <=10 fn test_ functions.
```

## Acceptance Criteria

- [ ] Original file replaced by {num_files} files, each with <=8 `fn test_` functions
- [ ] All original test cases preserved
- [ ] Each new file has the ADR-009 header comment
- [ ] CI workflow updated to reference the new filenames
- [ ] CI group passes reliably
"""
    result = subprocess.run(
        ["gh", "issue", "create", "--title", title, "--body", body,
         "--label", "bug", "--label", "testing", "--label", "ci-cd"],
        capture_output=True, text=True
    )
    issue_url = result.stdout.strip()
    print(f"Created #{issue_url.split('/')[-1]}: {title}")

# Run in explicit index-range batches -- NEVER background this loop
for file_path, test_count, ci_group, run_ids in VIOLATING_FILES[0:20]:
    create_issue(file_path, test_count, ci_group, run_ids)
```

**Critical**: Run `python3 script.py --start 0 20`, then `--start 20 40`, etc. Never use `run_in_background=True` — 502 errors + early termination cause the script to re-run from index 0, generating duplicate waves.

#### Step 5: Deduplicate if duplicates were created

```bash
gh issue list --label "ci-cd" --search "Mojo heap corruption" --state open \
  --limit 200 --json number,title | python3 -c "
import sys, json
from collections import defaultdict
issues = json.load(sys.stdin)
by_title = defaultdict(list)
for i in issues:
    by_title[i['title']].append(i['number'])
to_close = []
for title, nums in sorted(by_title.items()):
    if len(nums) > 1:
        keep = sorted(nums)[0]
        for n in sorted(nums)[1:]:
            to_close.append(n)
            print(f'Close #{n} (keep #{keep}): {title[:60]}')
print('Close IDs:', ' '.join(str(n) for n in to_close))
"
# Then close them:
for num in <ids>; do gh issue close "$num" --comment "Duplicate."; done
```

## Key Patterns

**False completion in commit messages**: Split commit messages often say "All N tests preserved" even when they aren't. Always verify with `comm -23` rather than trusting commit messages.

**Tests present under different names**: `test_operators_preserve_shape` and `test_unary_ops_preserve_shape` are different tests despite similar intent. The `comm -23` diff catches this correctly — a name change is NOT the same as preservation.

**Split files may exceed deprecated count**: Later commits often add new tests to split files. This is expected and correct. The audit only checks for tests in deprecated but not in any split file.

**Wildcard CI patterns absorb new split files**: CI workflows using `test_extensor_*.mojo` wildcards automatically pick up new split files. Only explicit filename lists need updating when a new split file is added.

**Stale issue plans**: Issue plans reflect a point-in-time snapshot. Between plan generation and implementation, other PRs may have already fixed some issues. Always re-audit current state.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assumed split was complete | Checked only that the original file was deleted and new files existed in CI workflow | 3 tests were silently dropped; count 13 ≠ 16 | Always compare `git show <split_commit> \| grep "^-fn test_"` count vs split file count |
| Checked only the primary file | Audited only the issue's specified file for violations | A sibling file in the same CI group still violated ADR-009 | Always audit ALL files in the CI group, not just the issue's primary file |
| Prose docstring as ADR-009 header | Used `"Note: Split from X due to ADR-009"` in docstring | Issue spec requires exact `# ADR-009:` comment block format | Check acceptance criteria for exact header format requirements |
| Trusted commit message | Assumed "All 21 tests preserved" in split commit message was accurate | Commit message was aspirational; actual audit found 1 dropped test in extensor splits | Always verify with `comm -23` diff, never trust commit message counts |
| Searched only .DEPRECATED files | Looked only for `.DEPRECATED` marker files to find deprecated sources | `test_backward.mojo` was deleted entirely (no `.DEPRECATED` left); required `git log --diff-filter=D` | Check both `.DEPRECATED` files AND git-deleted files |
| Checking files individually | Manually read each split file looking for missing tests | Error-prone, slow, easy to miss tests with similar names | Use `comm -23` set difference for reliable gap detection |
| Assuming plan was current | Implemented the issue plan directly without re-auditing | Earlier PRs had already fixed some issues in the plan | Always re-audit current state; plan may be stale |
| Fix only the issue-specified file | Addressed only the file named in the issue | That file was already split; sibling files `test_extensor_slicing.mojo` (19) and `test_extensor_unary_ops.mojo` (12) still violated ADR-009 | Always audit ALL files in the family, not just the one named in the issue |
| Background batch script | Used `run_in_background=True` for the 60-file batch issue creation | 502 GitHub API errors caused early exit; task system re-ran from index 0, creating 3 duplicate waves (41 + 64 + 8 duplicates) | Never background a sequential issue-creation loop — run synchronously with explicit `--start N M` index ranges |
| Single large batch | Ran all 115 files in one `--start 0 115` call | 502 error mid-run then background re-execution from 0 | Break into batches of <=20 and run each synchronously |
| Checking background output files | Tried `strings` and `grep` on persisted task output | GitHub 502 HTML bodies polluted the output making grep/strings useless | After any background run, use `gh issue list` to authoritatively check what was created |
| Using `_part1`/`_part2` naming | Issue body suggested `_part1` naming | Generic names lose semantic context about what tests are in each file | Use descriptive semantic suffixes (`_1d`, `_2d`, `_edge`) when groupings are clear |
| Leaving extensor files in "Core Utilities" | Split files were added to the existing large group | "Core Utilities" had 26 files — poor failure signal isolation | Create a dedicated CI group for the file family after splitting |

## Results & Parameters

### Issue Creation Audit (2026-03-06, ProjectOdyssey)

| Metric | Value |
|--------|-------|
| Files audited | ~650 test files |
| Files violating ADR-009 (>10 tests) | 131 |
| Issues created | 131 file-split + 1 wildcard overlap = **132** |
| Duplicates created (and closed) | 105 |
| Labels applied | `bug`, `testing`, `ci-cd` |
| Issue numbers | #3396–#3640 |
| Tracking issue updated | #3330 |

### Script Parameters

```python
LIMIT = 10          # ADR-009 max fn test_ per file
TARGET = 8          # split target (buffer below limit)
BATCH_SIZE = 20     # max files per synchronous run
LABELS = ["bug", "testing", "ci-cd"]
```

### Split Audit Results (2026-03-15, ProjectOdyssey)

| Deprecated File | Deprecated Count | Split Count | Missing |
|---|---|---|---|
| `test_backward.mojo` (git history) | 21 | 23 (+2 new) | **0** |
| `test_gradient_checking.mojo.DEPRECATED` | 16 | 19 (+3 new) | **0** |
| `test_gradient_validation.mojo.DEPRECATED` | 12 | 12 | **0** |
| `test_extensor_new_methods.mojo.DEPRECATED` | 15 | 15 | **0** |
| `test_extensor_operators.mojo.DEPRECATED` | 21 | 21 | **0** |
| `test_extensor_unary_ops.mojo.DEPRECATED` | 7 | 6→**7** | **1 fixed** |

**Fix applied**: Added `test_unary_ops_preserve_shape` to `test_extensor_neg_pos.mojo` (5→6 tests).

### Family Audit Results (2026-03-07, Issue #3476, ProjectOdyssey)

```text
test_extensor_slicing.mojo: 19 tests → 3 files (8, 6, 5)
test_extensor_unary_ops.mojo: 12 tests → 2 files (5, 7)
New "Core ExTensor" CI group: 10 files, all <=10 tests
"Core Utilities" group: extensor files removed (was 26 files)
```

### Split Recovery Results (2026-03-07, Issue #3444, ProjectOdyssey)

| Metric | Value |
|--------|-------|
| Original test count | 16 |
| Tests in initial split | 13 (3 dropped) |
| Dropped test names | `test_relu_mixed_inputs`, `test_conv2d_gradient_fp16`, `test_cross_entropy_gradient_fp16` |
| Secondary violation | `test_gradient_validation.mojo` — 12 tests (found via CI group audit) |
| Final split result | 4 files: 9, 7, 8, 4 tests |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | ADR-009 codebase-wide audit, issue creation (#3396–#3640), tracking issue #3330 | 131 violations found, 132 issues created |
| ProjectOdyssey | Issue #3476, extensor family audit and CI group creation | Semantic splits and dedicated "Core ExTensor" CI group |
| ProjectOdyssey | Issue #3444, gradient checking split recovery | 3 dropped tests recovered from git history |
| ProjectOdyssey | PR #4877, split completeness audit across all deprecated files | 1 dropped test found and fixed |

**Related:** `adr009-test-file-split-workflow` (full historical reference), `docs/adr/ADR-009-heap-corruption-workaround.md`, issue #2942
