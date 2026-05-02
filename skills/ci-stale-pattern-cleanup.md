---
name: ci-stale-pattern-cleanup
description: "Use when: (1) a CI matrix has patterns that may reference renamed or deleted test files (detect stale), (2) a test file was deleted but still appears in a GitHub Actions workflow pattern string (remove stale), (3) closing a cleanup issue where the only remaining work is a dangling workflow reference, (4) adding an inverse CI coverage check that flags matrix patterns matching zero existing files as warnings."
category: ci-cd
date: 2026-03-28
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - ci-cd
  - github-actions
  - stale-patterns
  - cleanup
  - validate-coverage
---

# CI Stale Pattern Cleanup

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-28 |
| **Objective** | Consolidated skill for detecting and removing stale CI patterns — patterns that reference renamed or deleted test files |
| **Outcome** | Merged from 2 source skills: stale-ci-pattern-detection, stale-ci-pattern-removal |
| **Verification** | unverified |

## When to Use

- A CI matrix YAML lists `path` + `pattern` entries and files may have been renamed or deleted
- You already have a forward check (uncovered test files) and want the inverse (unused patterns)
- A GitHub issue asks to "remove a test file entirely" and the file no longer exists on disk
- CI workflow contains a space-separated pattern string that lists individual test filenames
- The only remaining work to close an issue is removing a stale filename from a YAML workflow
- A cleanup/deprecation issue where the test file itself is already gone

## Verified Workflow

### Quick Reference

```bash
# 1. Confirm the file is actually gone (do not assume)
ls <project-root>/tests/shared/core/test_<name>.mojo 2>/dev/null || echo "File does not exist"

# 2. Find all references
grep -r "test_<name>" . --include="*.yml" --include="*.yaml" --include="*.toml" --include="*.mojo"

# 3. Run stale pattern check
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from validate_test_coverage import parse_ci_matrix, check_stale_patterns
from pathlib import Path
root = Path('.')
groups = parse_ci_matrix(root / '.github/workflows/comprehensive-tests.yml')
stale = check_stale_patterns(groups, root)
print('Stale:' if stale else 'No stale patterns')
for s in stale: print(f'  {s}')
"
```

### A. Detecting Stale Patterns (Adding to Validation Script)

Add `check_stale_patterns()` to `scripts/validate_test_coverage.py` as an inverse coverage check — patterns that expand to zero files are stale.

**Implementation** (add before `check_coverage()`):

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

**Wire into `main()` after the forward check** — print warnings to stderr (does not change exit code):

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

**Write pytest tests** using `tmp_path` fixture:

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

**Key design decisions**:

| Decision | Choice | Rationale |
| ---------- | -------- | ----------- |
| Exit code | No change (warnings only) | Stale patterns are advisory; only missing coverage blocks CI |
| Output stream | `sys.stderr` | Keeps stdout clean for downstream consumers |
| Return type | `List[str]` (sorted group names) | Stable, testable, easy to iterate |
| Deduplication | Handled by `expand_pattern()` returning `Set[Path]` | No extra logic needed |

### B. Removing Stale Filename References

Use when a test file was deleted but its name still appears in CI workflow pattern strings.

1. **Confirm the file is actually gone** — do not assume the issue description is current:
   ```bash
   ls <project-root>/tests/shared/core/test_<name>.mojo 2>/dev/null || echo "File does not exist"
   ```

2. **Grep for all references** to find every place the filename appears:
   ```bash
   grep -r "test_<name>" . \
     --include="*.yml" --include="*.yaml" \
     --include="*.toml" --include="*.mojo" \
     -l
   ```

3. **Edit the workflow file** — remove only the stale filename token from the pattern string. Pattern strings are space-separated; remove the token and its surrounding space.

   Use the Edit tool (not sed) to make a precise, reviewable change:
   ```
   # Before:
   pattern: "test_backward_linear.mojo test_backward_conv_pool.mojo test_backward_compat_aliases.mojo test_backward_losses.mojo"
   # After:
   pattern: "test_backward_linear.mojo test_backward_conv_pool.mojo test_backward_losses.mojo"
   ```

4. **Verify no remaining references** (excluding prompt/issue files):
   ```bash
   grep -r "test_<name>" . --include="*.yml" --include="*.toml" --include="*.mojo"
   ```

5. **Commit, push, create PR**:
   ```bash
   # Branch naming
   git checkout -b <issue-number>-remove-stale-ci-pattern

   # Commit
   git add .github/workflows/comprehensive-tests.yml
   git commit -m "refactor(tests): remove <test_filename> from CI

   The test file <path> has been deleted; this removes the dangling
   reference from the CI workflow pattern string.

   Closes #<issue>"

   git push -u origin <branch>
   gh pr create --title "refactor(tests): remove <test_filename> from CI" \
     --body "Closes #<issue>"
   gh pr merge --auto --rebase <pr-number>
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A for `check_stale_patterns` implementation | Implementation was straightforward on first attempt | — | Reusing `expand_pattern()` directly avoided any duplication |
| Glob for the file in worktree before confirming deletion | `Glob tests/shared/core/test_backward_compat_aliases.mojo` | File did not exist — already deleted in a prior commit | Always verify file existence first; issue descriptions may lag behind actual state |
| Background `find` command for existence check | Used `find /home/... -name "test_backward_compat_aliases.mojo"` as background task | Output wasn't available when needed | For quick existence checks, use `ls` or `Glob` synchronously |

## Results & Parameters

### Key Design: Warnings Only, Not Errors

Exit code behavior for `check_stale_patterns`:
- `0` = clean (both forward and inverse checks clean)
- `1` = only when forward check fails (uncovered test files)
- Stale patterns are printed to stderr as warnings — they are advisory, not blockers

This is intentional: stale patterns are a hygiene issue (dead references), not a coverage failure.

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

### Minimal Commit Message Template

```
refactor(tests): remove <test_filename> from CI

The test file <path> has been deleted; this removes the dangling
reference from the CI workflow pattern string.

Closes #<issue>
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3357, PR #4001 | stale-ci-pattern-detection implementation (13 tests pass) |
| ProjectOdyssey | Cleanup issues | stale-ci-pattern-removal for deleted test files |
