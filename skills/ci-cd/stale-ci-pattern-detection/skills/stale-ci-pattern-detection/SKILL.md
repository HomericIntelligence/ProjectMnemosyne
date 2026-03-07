---
name: stale-ci-pattern-detection
description: "Add inverse CI coverage check that flags matrix patterns matching zero existing files as warnings. Use when: CI matrix has patterns that may reference renamed/deleted files, or you want both forward and inverse coverage checks."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | CI matrix patterns referencing non-existent files silently pass, hiding stale entries after file renames or deletions |
| **Solution** | Inverse coverage check: expand each CI pattern and flag those matching 0 files as warnings |
| **Exit code behaviour** | Warnings only — does not change exit code; only uncovered test files (forward check) cause exit 1 |
| **Key function** | `check_stale_patterns(ci_groups, root_dir) -> List[str]` |
| **Language** | Python 3.7+ |
| **Test count** | 13 pytest tests (9 for `check_stale_patterns`, 4 regression for `expand_pattern`) |

## When to Use

- A CI matrix YAML lists `path` + `pattern` entries and files may have been renamed/deleted
- You already have a forward check (uncovered test files) and want the inverse (unused patterns)
- You want warnings that are visible in CI logs without blocking the build
- Implementing or extending a `validate_test_coverage.py`-style script

## Verified Workflow

### 1. Reuse the existing `expand_pattern()` helper

If you already have a function that globs a `(base_path, pattern)` pair against the repo root,
the inverse check is trivially built on top of it:

```python
def check_stale_patterns(
    ci_groups: Dict[str, Dict[str, str]], root_dir: Path
) -> List[str]:
    """
    Check for CI matrix patterns that match 0 existing test files.

    Returns:
        Sorted list of group names whose patterns match no existing files.
    """
    stale = []
    for group_name, group_info in ci_groups.items():
        matched = expand_pattern(group_info["path"], group_info["pattern"], root_dir)
        if not matched:
            stale.append(group_name)
    return sorted(stale)
```

### 2. Call it in main() after the forward check — print to stderr

```python
stale_patterns = check_stale_patterns(ci_groups, repo_root)
if stale_patterns:
    print("=" * 70, file=sys.stderr)
    print("Warning: Stale CI Patterns", file=sys.stderr)
    print("=" * 70, file=sys.stderr)
    print(file=sys.stderr)
    print(
        f"WARNING: Found {len(stale_patterns)} CI pattern(s) matching 0 files:",
        file=sys.stderr,
    )
    print(file=sys.stderr)
    for group_name in stale_patterns:
        group_info = ci_groups[group_name]
        print(
            f"   * {group_name!r}  "
            f"(path={group_info['path']!r}, pattern={group_info['pattern']!r})",
            file=sys.stderr,
        )
    print(file=sys.stderr)
    print(
        "Remove or update these entries in .github/workflows/comprehensive-tests.yml",
        file=sys.stderr,
    )
    print("=" * 70, file=sys.stderr)
    print(file=sys.stderr)
# Exit code unchanged — only forward check (uncovered files) returns 1
```

### 3. Write pytest tests using tmp_path fixture

```python
@pytest.fixture()
def tmp_repo(tmp_path: Path) -> Path:
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "tests" / "unit" / "test_foo.mojo").touch()
    (tmp_path / "tests" / "integration").mkdir(parents=True)
    (tmp_path / "tests" / "integration" / "test_baz.mojo").touch()
    return tmp_path

def test_stale_when_path_does_not_exist(tmp_repo):
    ci_groups = {"Ghost": {"path": "tests/nonexistent", "pattern": "test_*.mojo"}}
    assert check_stale_patterns(ci_groups, tmp_repo) == ["Ghost"]

def test_no_stale_when_all_patterns_match(tmp_repo):
    ci_groups = {
        "Unit": {"path": "tests/unit", "pattern": "test_*.mojo"},
        "Integration": {"path": "tests/integration", "pattern": "test_*.mojo"},
    }
    assert check_stale_patterns(ci_groups, tmp_repo) == []

def test_multiple_stale_sorted(tmp_repo):
    ci_groups = {
        "Zebra": {"path": "tests/z_gone", "pattern": "test_*.mojo"},
        "Alpha": {"path": "tests/a_gone", "pattern": "test_*.mojo"},
        "Good":  {"path": "tests/unit",   "pattern": "test_*.mojo"},
    }
    assert check_stale_patterns(ci_groups, tmp_repo) == ["Alpha", "Zebra"]
```

### 4. Pre-commit hook picks it up automatically

If `validate_test_coverage.py` is already wired into pre-commit, stale-pattern warnings
appear in hook output without needing any hook changes (warnings go to stderr, exit code stays 0).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Implementation was straightforward on the first attempt | — | Reusing `expand_pattern()` directly avoided any duplication or complexity |

## Results & Parameters

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Exit code | No change (warnings only) | Issue says "flag as warning"; only forward failures should block CI |
| Output stream | `sys.stderr` | Keeps stdout clean for downstream consumers; warnings are diagnostic |
| Return type | `List[str]` (sorted group names) | Stable, testable, easy to iterate in `main()` |
| Deduplication | Handled by `expand_pattern()` returning a `Set[Path]` | No extra logic needed |

### Copy-Paste Test Template

```python
# tests/scripts/test_validate_test_coverage.py
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from validate_test_coverage import check_stale_patterns, expand_pattern

@pytest.fixture()
def tmp_repo(tmp_path):
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "tests" / "unit" / "test_foo.mojo").touch()
    return tmp_path

class TestCheckStalePatterns:
    def test_empty_ci_groups(self, tmp_repo):
        assert check_stale_patterns({}, tmp_repo) == []

    def test_all_match(self, tmp_repo):
        ci_groups = {"Unit": {"path": "tests/unit", "pattern": "test_*.mojo"}}
        assert check_stale_patterns(ci_groups, tmp_repo) == []

    def test_missing_path(self, tmp_repo):
        ci_groups = {"Ghost": {"path": "tests/gone", "pattern": "test_*.mojo"}}
        assert check_stale_patterns(ci_groups, tmp_repo) == ["Ghost"]
```
