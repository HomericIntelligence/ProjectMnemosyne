---
name: ci-cd-promote-subgroups-to-matrix
description: "Promote subdirectory-scoped test patterns into separate CI matrix entries with leaf-level wildcards for auto-discovery. Use when: (1) a single matrix group uses multi-pattern strings covering subdirectories, (2) new test files are silently missed because they're not in the explicit pattern list, (3) you want each subdirectory to be its own CI job with test_*.mojo auto-discovery."
category: ci-cd
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-precommit
supersedes: []
tags:
  - ci-cd
  - github-actions
  - test-matrix
  - auto-discovery
  - wildcard-patterns
---

# Promote Sub-Groups to CI Matrix Entries

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Replace a single monolithic CI matrix group that uses explicit multi-pattern strings with separate per-subdirectory matrix entries using leaf-level `test_*.mojo` wildcards |
| **Outcome** | Successful — 1 group split into 6, all 52 files covered, zero overlap, `validate_test_coverage.py` passes |
| **Verification** | verified-precommit |

## When to Use

- A CI matrix group covers multiple subdirectories via a compound pattern like `test_*.mojo datasets/test_*.mojo samplers/test_*.mojo`
- New test files added to subdirectories are silently missed because they aren't in the explicit pattern list
- You want each subdirectory to auto-discover new files via simple `test_*.mojo` wildcards
- The inverse of `consolidate-ci-matrix` — splitting for auto-discovery rather than merging for job reduction

## Verified Workflow

> **Note:** Verified through pre-commit hooks and local coverage validation. CI validation pending on PR #5116.

### Quick Reference

```bash
# 1. Identify the monolithic group in comprehensive-tests.yml
grep -A 3 'name: "Data"' .github/workflows/comprehensive-tests.yml

# 2. List subdirectories to promote
ls tests/shared/data/

# 3. Count files per subdirectory (verify coverage)
python3 -c "
from pathlib import Path
for d in ['tests/shared/data'] + sorted([str(p) for p in Path('tests/shared/data').iterdir() if p.is_dir()]):
    files = list(Path('.').glob(f'{d}/test_*.mojo'))
    print(f'{d}: {len(files)} files')
"

# 4. After editing YAML, validate coverage
python3 scripts/validate_test_coverage.py

# 5. Verify no overlap between groups
python3 -c "
from pathlib import Path
groups = {
    'Parent': ('tests/shared/data', 'test_*.mojo'),
    'Sub1': ('tests/shared/data/datasets', 'test_*.mojo'),
    # ... add all subdirectories
}
all_files = set()
for name, (path, pat) in groups.items():
    for f in Path('.').glob(f'{path}/{pat}'):
        assert str(f) not in all_files, f'OVERLAP: {f}'
        all_files.add(str(f))
print(f'Total: {len(all_files)} files, no overlaps')
"
```

### Detailed Steps

1. **Read the current matrix entry** — identify the compound pattern covering subdirectories
2. **List all subdirectories** under the parent path that contain test files
3. **Create one matrix entry per subdirectory** — each with `path:` pointing to the leaf directory and `pattern: "test_*.mojo"`
4. **Create a "Core" entry** for top-level files — the parent path with `test_*.mojo` (non-recursive glob means no overlap with subdirectory entries)
5. **Preserve flags** — copy `continue-on-error: true` or other flags from the original entry to all new entries
6. **Validate coverage** — run `python3 scripts/validate_test_coverage.py` (must exit 0)
7. **Verify no overlap** — `Path.glob("dir/test_*.mojo")` is non-recursive, so parent and subdirectory entries never match the same files
8. **Run pre-commit hooks** — `just pre-commit-all` to validate YAML, coverage, and formatting

### Key Insight: Non-Recursive Glob Prevents Overlap

`Path.glob("tests/shared/data/test_*.mojo")` only matches files directly in `tests/shared/data/`, NOT files in `tests/shared/data/datasets/`. This is because `test_*.mojo` has no `**` component, so the glob is non-recursive. This means a parent "Core" entry and subdirectory entries will never overlap — each file is matched by exactly one group.

The same behavior applies to the justfile's bash glob (`$TEST_PATH/$pattern`), which is also non-recursive without `**`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A — first approach succeeded | Replaced single group with 6 leaf-level entries | Did not fail | Verify glob non-recursiveness before assuming zero overlap; always run `validate_test_coverage.py` |

## Results & Parameters

### Before (1 group)

```yaml
- name: "Data"
  path: "tests/shared/data"
  pattern: "test_*.mojo datasets/test_*.mojo samplers/test_*.mojo transforms/test_*.mojo loaders/test_*.mojo formats/test_*.mojo"
```

### After (6 groups)

```yaml
- name: "Data Core"
  path: "tests/shared/data"
  pattern: "test_*.mojo"
  continue-on-error: true
- name: "Data Datasets"
  path: "tests/shared/data/datasets"
  pattern: "test_*.mojo"
  continue-on-error: true
- name: "Data Loaders"
  path: "tests/shared/data/loaders"
  pattern: "test_*.mojo"
  continue-on-error: true
- name: "Data Transforms"
  path: "tests/shared/data/transforms"
  pattern: "test_*.mojo"
  continue-on-error: true
- name: "Data Samplers"
  path: "tests/shared/data/samplers"
  pattern: "test_*.mojo"
  continue-on-error: true
- name: "Data Formats"
  path: "tests/shared/data/formats"
  pattern: "test_*.mojo"
  continue-on-error: true
```

### File Coverage

| Group | Path | Files |
|-------|------|-------|
| Data Core | `tests/shared/data` | 13 |
| Data Datasets | `tests/shared/data/datasets` | 8 |
| Data Loaders | `tests/shared/data/loaders` | 5 |
| Data Transforms | `tests/shared/data/transforms` | 18 |
| Data Samplers | `tests/shared/data/samplers` | 6 |
| Data Formats | `tests/shared/data/formats` | 2 |
| **Total** | | **52** |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #4458, PR #5116 | Split monolithic Data CI group into 6 sub-groups for auto-discovery |
