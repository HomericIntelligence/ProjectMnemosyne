---
name: ci-matrix-overlap-detection
description: 'Detect overlapping patterns in GitHub Actions CI matrix groups. Use
  when: adding subdirectory wildcard patterns to matrix groups, auditing for duplicate
  test runs, or implementing lint to prevent a parent group from silently covering
  files owned by a child group.'
category: ci-cd
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
# Skill: CI Matrix Overlap Detection

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-15 |
| Category | ci-cd |
| Outcome | Success |
| Project | ProjectOdyssey |

When a GitHub Actions workflow uses a matrix strategy for test groups, parent groups
that use subdirectory wildcards (e.g. `pattern: "subdir/test_*.mojo"`) can silently
duplicate files already covered by dedicated child groups. This causes tests to run
twice, inflates CI time, and masks true coverage. Adding pairwise overlap detection
to the coverage validation script catches this class of regression automatically.

## When to Use

- You are adding a new test matrix group with subdirectory wildcard patterns
- A parent matrix group uses `path: tests/shared` with `pattern: subdir/test_*.mojo`
  alongside a dedicated group with `path: tests/shared/subdir`
- You want a pre-commit/CI gate that fails if any file is matched by more than one group
- Following up on a regression where the same tests ran in multiple CI jobs (issue #3640 pattern)

## Verified Workflow

### Quick Reference

```python
# Core algorithm — add to existing coverage validation script
def check_group_overlaps(
    ci_groups: Dict[str, Dict[str, str]],
    coverage_by_group: Dict[str, Set[Path]],
) -> List[Tuple[str, str, Path]]:
    overlaps = []
    group_names = sorted(coverage_by_group.keys())
    for i, name_a in enumerate(group_names):
        path_a = ci_groups[name_a]["path"]
        files_a = coverage_by_group[name_a]
        for name_b in group_names[i + 1:]:
            path_b = ci_groups[name_b]["path"]
            files_b = coverage_by_group[name_b]
            if not _paths_overlap(path_a, path_b):
                continue          # skip unrelated dirs — no false positives
            for f in sorted(files_a & files_b):
                overlaps.append((name_a, name_b, f))
    return overlaps
```

### Step 1 — Add `_paths_overlap()` helper

Only compare groups whose `path:` values share a common prefix. This avoids false positives
between unrelated directories (e.g. `benchmarks/` vs `tests/`).

```python
def _paths_overlap(path_a: str, path_b: str) -> bool:
    """Return True if one path is a prefix of the other (or they are equal)."""
    a, b = Path(path_a), Path(path_b)
    try:
        a.relative_to(b)
        return True
    except ValueError:
        pass
    try:
        b.relative_to(a)
        return True
    except ValueError:
        pass
    return False
```

### Step 2 — Sort `pathlib.glob()` results

`pathlib.glob()` ordering is non-deterministic across platforms. Sort before consuming:

```python
# Before
for match in root_dir.glob(full_pattern):

# After
for match in sorted(root_dir.glob(full_pattern)):
```

### Step 3 — Wire into `main()` before coverage check

Call overlap detection after building `coverage_by_group` and exit 1 if any overlaps found.
Report overlaps **before** uncovered-file errors so they are seen first.

```python
overlaps = check_group_overlaps(ci_groups, coverage_by_group)
if overlaps:
    for group_a, group_b, f in overlaps:
        print(f"   • {f}")
        print(f"     → matched by '{group_a}' AND '{group_b}'")
    return 1
```

### Step 4 — Fix detected overlaps

Remove the redundant combined group. In the #3640 regression, an "Autograd & Benchmarking"
group with `path: tests/shared` and `pattern: autograd/test_*.mojo benchmarking/test_*.mojo`
duplicated dedicated "Autograd" and "Benchmarking" groups. The fix is to delete the combined
group — the dedicated groups already provide full coverage.

```yaml
# REMOVE this redundant combined group:
- name: "Autograd & Benchmarking"
  path: "tests/shared"
  pattern: "autograd/test_*.mojo benchmarking/test_*.mojo"

# KEEP the dedicated groups:
- name: "Autograd"
  path: "tests/shared/autograd"
  pattern: "test_*.mojo"
- name: "Benchmarking"
  path: "tests/shared/benchmarking"
  pattern: "test_*.mojo"
```

### Step 5 — Add `check_stale_patterns()` (companion function)

If the test file imports `check_stale_patterns`, add it as well — it detects groups whose
patterns match zero files (renamed/deleted test dirs):

```python
def check_stale_patterns(
    ci_groups: Dict[str, Dict[str, str]],
    root_dir: Path,
) -> List[str]:
    stale: List[str] = []
    for group_name, group_info in ci_groups.items():
        matched = expand_pattern(group_info["path"], group_info["pattern"], root_dir)
        if not matched:
            stale.append(group_name)
    return sorted(stale)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #4459 / PR #4885 | [notes.md](../references/notes.md) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Compare all group pairs unconditionally | Pairwise intersection of all groups regardless of their `path:` values | Generates false positives between unrelated dirs (e.g. `benchmarks/` and `tests/`) that share no files but confuse the algorithm | Only compare groups whose `path:` values share a common prefix via `_paths_overlap()` |
| Use unsorted `pathlib.glob()` | Relied on `root_dir.glob()` iteration order for determinism | `pathlib.glob()` ordering is implementation-defined and non-deterministic across OS / Python versions | Always wrap `root_dir.glob()` in `sorted()` before consuming results |
| Add a new dedicated lint script | Created a separate `scripts/lint_ci_matrix_overlaps.py` | Duplicate parsing logic for the CI YAML, harder to maintain two scripts, separate pre-commit entry needed | Extend the existing `validate_test_coverage.py` — it already parses the matrix and resolves glob patterns |

## Results & Parameters

**25 tests pass** across `TestCheckStalePatterns`, `TestExpandPattern`, `TestPathsOverlap`,
and `TestCheckGroupOverlaps` after implementation.

**Key function signatures**:

```python
def _paths_overlap(path_a: str, path_b: str) -> bool: ...

def check_group_overlaps(
    ci_groups: Dict[str, Dict[str, str]],      # group name → {path, pattern}
    coverage_by_group: Dict[str, Set[Path]],   # group name → set of matched files
) -> List[Tuple[str, str, Path]]:              # (group_a, group_b, file) triples
    ...

def check_stale_patterns(
    ci_groups: Dict[str, Dict[str, str]],
    root_dir: Path,
) -> List[str]:                                # sorted list of stale group names
    ...
```

**Exit codes**: `0` = clean (no overlaps, no uncovered files); `1` = errors found.

**Pre-commit integration**: No new hook entry needed — the existing `validate-test-coverage`
hook runs `scripts/validate_test_coverage.py` which now includes overlap detection.
