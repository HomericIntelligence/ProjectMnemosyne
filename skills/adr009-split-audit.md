---
name: adr009-split-audit
description: 'Audit Mojo test files for ADR-009 compliance, create GitHub issues for violations,
  split files, verify no tests were dropped, and recover missing tests. Use when: (1) CI
  is failing due to Mojo heap corruption linked to per-file test count violations, (2) an
  ADR mandates a test limit and you need to enumerate all violations as actionable issues,
  (3) investigating whether a test file split omitted any test functions, (4) verifying that
  all tests from a deprecated file are present in successor split files, (5) a split was
  previously done but tests are still failing or the issue remains open, (6) the post-split
  test count does not match the original file count, (7) other test files in the same CI group
  also violate ADR-009, (8) fixing an ADR-009 violation and sibling files may also exceed
  the limit, (9) no dedicated CI group exists for the test family, (10) split files are
  buried in an overloaded CI group.'
category: testing
date: 2026-03-25
version: 1.0.0
user-invocable: false
tags:
  - adr-009
  - mojo
  - heap-corruption
  - test-splitting
  - ci-cd
  - audit
---
## Overview

| Field | Value |
|-------|-------|
| **Problem** | ADR-009 limits Mojo test files to <=10 `fn test_` functions to avoid heap corruption; violations cause flaky CI, splits can silently drop tests, and issues must be tracked per-file |
| **ADR** | ADR-009 -- max <=10 `fn test_` functions per `.mojo` file |
| **Scope** | Audit, issue creation, file splitting, post-split verification, dropped-test recovery, and CI group management |
| **Risk** | Dropped gradient/backward tests give false confidence; duplicate issue waves from backgrounded scripts; secondary violations in sibling files |

## When to Use

- CI on `main` fails 10+/20 runs with random group rotation (load-dependent heap corruption)
- An ADR specifies a per-file `fn test_` limit (e.g. <=10) and `grep -c "^fn test_"` shows 50+ files over the limit
- You need traceable, actionable issues for every violation before starting any splits
- After any ADR-009 test file split to verify completeness
- When investigating a CI failure that references a test that "should exist"
- After restoring from git history and finding fewer tests than expected
- Periodically as a health check on the test split inventory
- When opening a follow-up issue from a split PR (e.g., #3444 -> #4241)
- A split was completed (`.DEPRECATED` file exists, new files reference CI workflow), but the issue is still open
- The sum of `fn test_` counts in split files is less than the original file's count
- Other test files referenced in the same CI group also exceed 10 `fn test_` functions
- Split files are missing the required ADR-009 header comment block
- An issue asks to fix one ADR-009 file but related files in the same directory may also violate the limit
- Split files for a test family are scattered across an overloaded CI group
- No dedicated CI group exists for a family of related tests
- A CI group has >15 test files (risk of slow or flaky runs)
- After splitting, the original file needs to be tracked as `.DEPRECATED`

## Verified Workflow

### Quick Reference

```bash
# --- Audit: count violations ---
for f in $(find tests -name "test_*.mojo" | sort); do
  count=$(grep -c "^fn test_" "$f" 2>/dev/null || echo "0")
  if [ "$count" -gt 10 ]; then echo "$count $f"; fi
done | sort -rn

# --- Issue creation: batch create (synchronous, <=20 per batch) ---
python3 create_issues.py --start 0 20
# Then: --start 20 40, --start 40 60, etc. NEVER background this loop.

# --- Post-split audit: find dropped tests ---
# 1. Find deprecated files
find tests/ -name "*.DEPRECATED"

# 2. Extract test names from deprecated file
grep "^fn test_" <file>.DEPRECATED | sed 's/fn //; s/(.*$//' | sort > /tmp/dep.txt

# 3. Extract test names from active split files
grep -h "^fn test_" tests/shared/core/test_<prefix>*.mojo | sed 's/fn //; s/(.*$//' | sort > /tmp/split.txt

# 4. Find missing tests
comm -23 /tmp/dep.txt /tmp/split.txt

# 5. For files without .DEPRECATED (deleted in git), recover from history
git log --oneline --diff-filter=D -- "tests/**/<file>.mojo"
git show <parent-commit>^:<path>/<file>.mojo | grep "^fn test_"

# --- Comprehensive family audit ---
for f in tests/shared/core/test_<family>_*.mojo; do
  count=$(grep -c "^fn test_" "$f" 2>/dev/null || echo 0)
  echo "$f: $count tests"
done

# --- Recovery: get dropped test implementation ---
SPLIT_COMMIT=$(git log --oneline -- "tests/path/to/test_original.mojo" | head -1 | cut -d' ' -f1)
git show $SPLIT_COMMIT -- "tests/path/to/test_original.mojo" | grep "^-fn test_"
git show $SPLIT_COMMIT -- "tests/path/to/test_original.mojo" | grep -A 40 "^-fn test_missing_name"

# --- Deduplication: find and close duplicate issues ---
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
```

### Step 1: Count violations across the codebase

```bash
for f in $(find tests -name "test_*.mojo" | sort); do
  count=$(grep -c "^fn test_" "$f" 2>/dev/null || echo "0")
  if [ "$count" -gt 10 ]; then
    echo "$count $f"
  fi
done | sort -rn
```

### Step 2: Map files to CI groups

Read `.github/workflows/comprehensive-tests.yml` to extract which CI job runs each file. Record:
- CI group name
- Sample failing run IDs for that group (from CI failure history)

### Step 3: Check for existing issues (avoid duplicates)

```bash
gh issue list --label "ci-cd" --search "ADR-009" --state open --limit 200 --json number,title
```

### Step 4: Create issues synchronously in batches

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
    title = f"fix(ci): split {filename} ({test_count} tests) -- Mojo heap corruption (ADR-009)"
    body = make_issue_body(...)  # see Issue Body Template below
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

**Critical**: Run `python3 script.py --start 0 20`, then `--start 20 55`, etc. Never use
`run_in_background=True` for this loop -- 502 errors + early termination cause the script to
re-run from index 0, generating duplicate waves.

### Step 5: Audit the entire file family (comprehensive)

When fixing one file, audit ALL sibling files in the same directory:

```bash
for f in tests/shared/core/test_<family>_*.mojo; do
  count=$(grep -c "^fn test_" "$f" 2>/dev/null || echo 0)
  echo "$f: $count tests"
done
```

Fix ALL violators in one PR.

### Step 6: Determine split strategy

| Test count | Strategy |
|-----------|----------|
| 11-16 | 2-way split (<=8 each) |
| 17-24 | 3-way split (<=8 each) |
| 25+ | 4-way split (<=7 each) |

Prefer semantic suffix names over generic `_part1`/`_part2`:

```text
test_extensor_slicing.mojo (19 tests) ->
  test_extensor_slicing_1d.mojo    (8: basic + strided)
  test_extensor_slicing_2d.mojo    (6: multi-dim + batch)
  test_extensor_slicing_edge.mojo  (5: edge cases + copy semantics)
```

### Step 7: Add ADR-009 header to each new file

```mojo
# ADR-009: This file is intentionally limited to <=10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. Split from <original_file>.mojo. See docs/adr/ADR-009-heap-corruption-workaround.md
```

**Header format matters** -- prose docstrings mentioning ADR-009 are NOT equivalent to the required `# ADR-009:` comment block.

### Step 8: Rename originals to .DEPRECATED

```bash
git mv tests/path/test_original.mojo tests/path/test_original.mojo.DEPRECATED
```

This follows the established ADR-009 pattern and preserves git history.

### Step 9: Create or update dedicated CI group

In `.github/workflows/comprehensive-tests.yml`, add a new group **before** the overloaded group:

```yaml
# ---- <Family> tests (split per ADR-009 to avoid heap corruption) ----
- name: "Core ExTensor"
  path: "tests/shared/core"
  pattern: "test_extensor_slicing_1d.mojo test_extensor_slicing_2d.mojo ..."
```

Remove the same files from the overloaded group to avoid duplicate runs. Target <=10 files per CI group.

### Step 10: Post-split audit -- verify no tests were dropped

```bash
# Build original test set from .DEPRECATED or git history
grep "^fn test_" tests/shared/core/test_foo.mojo.DEPRECATED \
  | sed 's/fn //; s/(.*$//' | sort > /tmp/orig.txt

# For files deleted without .DEPRECATED marker:
SPLIT_COMMIT=$(git log --oneline -- "tests/path/to/test_original.mojo" | head -1 | cut -d' ' -f1)
git show $SPLIT_COMMIT -- "tests/path/to/test_original.mojo" | grep "^-fn test_" > /tmp/orig.txt

# Build split file test set
grep -h "^fn test_" tests/shared/core/test_foo_*.mojo \
  | sed 's/fn //; s/(.*$//' | sort > /tmp/split.txt

# Find gaps
comm -23 /tmp/orig.txt /tmp/split.txt
```

If non-empty: each line is a dropped test that must be recovered.

### Step 11: Recover dropped tests

For each dropped test, get the implementation from the deprecated file or git history:

```bash
grep -n "fn test_missing_test_name" tests/shared/core/test_foo.mojo.DEPRECATED
# Or from git:
git show $SPLIT_COMMIT -- "tests/path/to/test_original.mojo" | grep -A 40 "^-fn test_missing_name"
```

Strip the leading `-` (diff prefix) and add to the appropriate split file. Verify count stays <=10 after addition.

### Step 12: Deduplicate issues if duplicates were created

```bash
gh issue list --label "ci-cd" --search "Mojo heap corruption" --state open \
  --limit 200 --json number,title | python3 deduplicate.py
# Then close duplicates:
for num in <ids>; do gh issue close "$num" --comment "Duplicate."; done
```

### Step 13: Final verification

```bash
# Confirm per-file counts
grep -c "^fn test_[a-z]" tests/shared/core/test_*.mojo | grep -v ".DEPRECATED"

# Re-run gap check (should show 0 missing)
for deprecated in tests/shared/core/*.DEPRECATED; do
    echo "=== $deprecated ==="
    grep "^fn test_" "$deprecated" | sed 's/fn //; s/(.*$//' | sort > /tmp/dep_tests.txt
    grep -h "^fn test_" tests/shared/core/*.mojo 2>/dev/null \
        | sed 's/fn //; s/(.*$//' | sort > /tmp/split_tests.txt
    missing=$(comm -23 /tmp/dep_tests.txt /tmp/split_tests.txt)
    if [ -z "$missing" ]; then
        echo "All tests preserved"
    else
        echo "MISSING: $missing"
    fi
done

# Verify CI workflow references
grep -n "<family>" .github/workflows/comprehensive-tests.yml
```

## Issue Body Template

```markdown
## Problem

`{file_path}` contains **{test_count} `fn test_` functions**, exceeding the ADR-009 limit of 10 per file.

This causes intermittent heap corruption crashes in Mojo v0.26.1 (`libKGENCompilerRTShared.so`
JIT fault), making the **{ci_group}** CI group non-deterministically fail.

## Evidence

- **File**: `{file_path}`
- **Test count**: {test_count} (limit: 10, target after split: <=8)
- **CI Group**: `{ci_group}`
- **Sample failing run IDs**: {run_ids}
- **CI failure rate**: 13/20 recent runs on `main`

Related: #2942, ADR-009 (`docs/adr/ADR-009-heap-corruption-workaround.md`)

## Fix

Split `{file_path}` into **{num_files} files** of <=8 tests each:
  - `test_{base}_part1.mojo` (~8 tests)
  - `test_{base}_part2.mojo` (~8 tests)
  ...

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
```

## Key Patterns

### Pattern: False completion in commit messages

Split commit messages often say "All N tests preserved" even when they aren't. The commit author
counted tests in the new split files but may have missed gradient tests that require more
complex setup. Always verify with `comm -23` rather than trusting commit messages.

### Pattern: Tests present under different names

`test_operators_preserve_shape` (in `test_extensor_abs_ops.mojo`) and
`test_unary_ops_preserve_shape` (in deprecated) are different tests despite similar intent.
The comm-based diff catches this correctly -- a name change is not the same as preservation.

### Pattern: Split files may exceed deprecated count

Later commits often add new tests to split files. This is expected and correct. The audit
only checks for tests that exist in deprecated but not in any split file -- the reverse
(new tests in splits not in deprecated) is fine.

### Pattern: Wildcard CI patterns absorb new split files

CI workflows using `test_extensor_*.mojo` wildcards automatically pick up new split files.
Only workflows with explicit filename lists (like the "Core Gradient" group) need updating
when a new split file is added.

## Key Invariants

- **Always audit secondary files** in the same CI group -- they often have violations too
- **Always verify test counts** from git history before closing an issue
- **Dropped tests are silent** -- no compiler or CI error warns you; only manual count comparison reveals them
- **Header format matters** -- prose docstrings mentioning ADR-009 are NOT equivalent to the required comment block

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Background batch script | Used `run_in_background=True` for the 60-file batch | 502 GitHub API errors caused early exit; the task system then re-ran from index 0, creating 3 duplicate waves (41 + 64 + 8 duplicates) | Never background a sequential issue-creation loop -- run synchronously with explicit `--start N M` index ranges |
| Single large batch | Ran all 115 files in one `--start 0 115` call | Same problem: 502 error mid-run then background re-execution from 0 | Break into batches of <=20 and run each synchronously |
| Retry via inline Python | Used inline `python3 -c "exec(open(...)...)"` to retry single failures | Works fine for individual retries but obscures which issues were created | Use the script with `--start` args for all batch work |
| Checking background output files | Tried `strings` and `grep` on persisted task output (54KB HTML-heavy) | GitHub 502 HTML bodies polluted the output making grep/strings useless | After any background run, use `gh issue list` to authoritatively check what was created |
| Fix only the issue-specified file | Addressed only `test_extensor_new_methods.mojo` as listed in the issue | That file was already split in a previous commit; sibling files `test_extensor_slicing.mojo` (19) and `test_extensor_unary_ops.mojo` (12) still violated ADR-009 | Always audit ALL files in the family, not just the one named in the issue |
| Using `_part1`/`_part2` naming | Issue body suggested `test_extensor_new_methods_part1.mojo` as the naming convention | Generic names lose semantic context about what tests are in each file | Use descriptive semantic suffixes (`_1d`, `_2d`, `_edge`, `_neg_pos`, `_abs_ops`) |
| Leaving split files in overloaded CI group | Split files were added to the existing "Core Utilities" group | "Core Utilities" had 26 files -- too large, poor failure signal isolation | Create a dedicated CI group for the file family after splitting |
| Assuming issue file is unresolved | Treated `test_extensor_new_methods.mojo` as still needing splitting | It was already split in commit `8a78d3aa`; DEPRECATED file existed | Check git log for the target file before starting work: `git log --all --oneline -- path/to/file` |
| Trusted commit message | Assumed "All 21 tests preserved" in split commit message was accurate | Commit message was aspirational; actual audit found 1 dropped test in extensor splits | Always verify with `comm -23` diff, never trust commit message counts |
| Searched only .DEPRECATED files | Looked only for `.DEPRECATED` marker files to find deprecated sources | `test_backward.mojo` was deleted entirely (no `.DEPRECATED` left); required `git log --diff-filter=D` | Check both `.DEPRECATED` files AND git-deleted files |
| Checking files individually | Manually read each split file looking for missing tests | Error-prone, slow, easy to miss tests with similar names | Use `comm -23` set difference for reliable gap detection |
| Assuming plan was current | Issue plan said 10 tests were missing; checked those first | Earlier PRs (#127d8e02, d1420696) had already restored the backward and gradient_checking tests | Always re-audit current state from source; plan may be stale |
| Assumed split was complete | Checked only that the original file was deleted and new files existed in CI workflow | 3 tests were silently dropped; count 13 != 16 | Always compare `git show <split_commit> \| grep "^-fn test_"` count vs split file count |
| Checked only the primary file | Audited `test_gradient_checking.mojo` split files only | `test_gradient_validation.mojo` (12 tests, same CI group) was still violating ADR-009 | Always audit ALL files referenced in the CI group pattern, not just the issue's primary file |
| Prose docstring as ADR-009 header | Initial splits used `"Note: Split from X due to ADR-009"` in docstring | Issue spec requires exact `# ADR-009:` comment block format | Check issue acceptance criteria for exact header format requirements |

## Results & Parameters

### ADR-009 limits

- Hard limit: <=10 `fn test_` per file
- Target: <=8 for safety buffer
- Recovery test always fits if deprecated file had <=10 tests total

### Script parameters

```python
LIMIT = 10          # ADR-009 max fn test_ per file
TARGET = 8          # split target (buffer below limit)
BATCH_SIZE = 20     # max files per synchronous run
LABELS = ["bug", "testing", "ci-cd"]
```

### Issue creation audit (2026-03-06, ProjectOdyssey)

| Metric | Value |
|--------|-------|
| Files audited | ~650 test files |
| Files violating ADR-009 (>10 tests) | 131 |
| Issues created | 131 file-split + 1 wildcard overlap = **132** |
| Duplicates created (and closed) | 105 |
| Labels applied | `bug`, `testing`, `ci-cd` |
| Issue numbers | #3396--#3640 |
| Tracking issue updated | #3330 |

### Comprehensive family audit (2026-03-07, issue #3476)

```text
test_extensor_slicing.mojo: 19 tests -> 3 files (8, 6, 5)
test_extensor_unary_ops.mojo: 12 tests -> 2 files (5, 7)
New "Core ExTensor" CI group: 10 files, all <=10 tests
"Core Utilities" group: extensor files removed (was 26 files)
```

### Post-split recovery audit (2026-03-07, test_gradient_checking.mojo)

| Metric | Value |
|--------|-------|
| Original test count | 16 |
| Tests in initial split | 13 (3 dropped) |
| Dropped test names | `test_relu_mixed_inputs`, `test_conv2d_gradient_fp16`, `test_cross_entropy_gradient_fp16` |
| Secondary violation | `test_gradient_validation.mojo` -- 12 tests (found via CI group audit) |
| Final split result | 4 files: 9, 7, 8, 4 tests |

### Split completeness audit (2026-03-15, ProjectOdyssey)

| Deprecated File | Deprecated Count | Split Count | Missing |
|---|---|---|---|
| `test_backward.mojo` (git history) | 21 | 23 (+2 new) | **0** |
| `test_gradient_checking.mojo.DEPRECATED` | 16 | 19 (+3 new) | **0** |
| `test_gradient_validation.mojo.DEPRECATED` | 12 | 12 | **0** |
| `test_extensor_new_methods.mojo.DEPRECATED` | 15 | 15 | **0** |
| `test_extensor_operators.mojo.DEPRECATED` | 21 | 21 | **0** |
| `test_extensor_unary_ops.mojo.DEPRECATED` | 7 | 6->**7** | **1 fixed** |

**Fix applied**: Added `test_unary_ops_preserve_shape` to `test_extensor_neg_pos.mojo`
(5 -> 6 tests). PR: HomericIntelligence/ProjectOdyssey#4877

### Commit pattern

```bash
git commit -m "fix(ci): split <family> test files and add <Group> CI group (ADR-009)

Split <file>.mojo (<N> tests) into <M> files:
- <split_file_1>.mojo (<X> tests)
- <split_file_2>.mojo (<Y> tests)

Added dedicated '<Group>' CI group in comprehensive-tests.yml.
Old files renamed to .DEPRECATED per ADR-009 pattern.

Closes #<issue>
"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | ADR-009 codebase-wide audit, issue creation (#3396--#3640), tracking issue #3330 | 131 violations found, 132 issues created |
| ProjectOdyssey | Issue #3476, extensor family comprehensive audit and CI group creation | PR with semantic splits and dedicated "Core ExTensor" CI group |
| ProjectOdyssey | Issue #3444, gradient checking split recovery | 3 dropped tests recovered, secondary violation in test_gradient_validation.mojo |
| ProjectOdyssey | PR #4877, split completeness audit across all deprecated files | 1 dropped test found and fixed in test_extensor_unary_ops split |
