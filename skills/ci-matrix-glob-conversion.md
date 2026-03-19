---
name: ci-matrix-glob-conversion
description: 'Convert explicit CI matrix filename lists to glob patterns and implement
  check_stale_patterns(). Use when: CI matrix has explicit filename lists that need
  auto-discovery, or test files import a function that doesn''t yet exist in its target
  module.'
category: ci-cd
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Problem** | CI matrix has explicit filename list (`testing/test_fixtures_part1.mojo test_fixtures_part2.mojo ...`) instead of a glob; any new file requires manual workflow edits or the `validate-test-coverage` hook blocks commits |
| **Solution** | Replace explicit list with `testing/test_*.mojo` glob AND implement `check_stale_patterns()` in `validate_test_coverage.py` (test file already expected this function) |
| **Key insight** | Check whether the CI workflow fix already landed on `main` before implementing — the actual work may be in the Python script, not the YAML |
| **Language** | Python 3.7+ |
| **Test count** | 13 pytest tests (9 for `check_stale_patterns`, 4 regression for `expand_pattern`) |

## When to Use

- A CI matrix YAML entry for a subdirectory uses space-separated explicit filenames instead of a glob
- A `validate-test-coverage` hook blocks commits because new test files aren't listed explicitly
- A test module imports a function (e.g., `check_stale_patterns`) that doesn't exist yet in the script under test
- Converting ADR-009 split files (e.g., `test_foo_part1.mojo test_foo_part2.mojo test_foo_part3.mojo`) back to a glob after the pattern is stable

## Verified Workflow

### 1. Check whether the YAML change already landed

Before touching the workflow file, grep for the glob:

```bash
grep "testing/test_" .github/workflows/comprehensive-tests.yml
```

If `testing/test_*.mojo` already appears, the YAML change is done — proceed to step 2.

### 2. Identify what the test file expects

Check if a test file already exists that imports from the script:

```bash
python3 -m pytest tests/scripts/test_validate_test_coverage.py -v 2>&1 | head -20
```

`ImportError: cannot import name 'check_stale_patterns'` means the function is missing.

### 3. Implement check_stale_patterns() in the script

Add the function **before** `check_coverage()`, reusing the existing `expand_pattern()` helper:

```python
def check_stale_patterns(
    ci_groups: Dict[str, Dict[str, str]], root_dir: Path
) -> List[str]:
    """Check for CI matrix entries that match zero existing test files.

    A stale pattern is one whose base path does not exist or whose glob
    matches no files in the repository.

    Args:
        ci_groups: Mapping of group name -> {"path": ..., "pattern": ...}
                   as returned by parse_ci_matrix().
        root_dir:  Repository root path.

    Returns:
        Sorted list of group names whose patterns match zero files.
    """
    stale: List[str] = []
    for group_name, group_info in ci_groups.items():
        matched = expand_pattern(group_info["path"], group_info["pattern"], root_dir)
        if not matched:
            stale.append(group_name)
    return sorted(stale)
```

### 4. Verify all tests pass

```bash
pixi run python -m pytest tests/scripts/test_validate_test_coverage.py -v
# Expected: 13 passed

python3 scripts/validate_test_coverage.py
# Expected: exit 0, no output
```

### 5. Commit and open PR

```bash
git add scripts/validate_test_coverage.py
git commit -m "feat(ci): add check_stale_patterns() to validate_test_coverage script"
gh pr create --title "..." --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Modifying the workflow YAML | Planned to change explicit list to glob in comprehensive-tests.yml | Grep showed `testing/test_*.mojo` was already present — the YAML fix had already landed on main | Always grep the actual file before assuming the YAML needs editing |
| Assuming the issue was closed | The issue description described the YAML state before the fix; the branch was already up-to-date with main | Pre-existing test file (`test_validate_test_coverage.py`) imported `check_stale_patterns` which didn't exist | Run `pytest` first — ImportError from tests reveals the actual missing piece |

## Results & Parameters

### Decision Table

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Where to add function | Before `check_coverage()` | Natural ordering: stale check is the inverse of coverage check |
| Return type | `List[str]` (sorted) | Stable, testable output; callers iterate group names |
| Reuse `expand_pattern()` | Yes | Avoids duplicating glob logic; single source of truth |
| Exit code impact | None (warnings only) | Stale patterns are advisory; only missing coverage blocks CI |

### Diagnosis Command Sequence

```bash
# 1. Is the YAML already fixed?
grep "testing/test_" .github/workflows/comprehensive-tests.yml

# 2. Do tests reveal a missing function?
python3 -m pytest tests/scripts/ -v 2>&1 | grep -E "PASSED|FAILED|ERROR|ImportError"

# 3. Does the coverage script pass?
python3 scripts/validate_test_coverage.py; echo "Exit: $?"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #4246, PR #4878 | [notes.md](../../references/notes.md) |
