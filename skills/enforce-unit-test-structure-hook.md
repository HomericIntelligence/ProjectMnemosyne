---
name: enforce-unit-test-structure-hook
description: "Pattern for adding a pre-commit hook that enforces tests/unit/ mirroring\
  \ convention \u2014 fails on test_*.py files at the root level of the unit test\
  \ directory"
category: ci-cd
date: 2026-02-27
version: 1.0.0
user-invocable: false
---
# Enforce Unit Test Structure via Pre-commit Hook

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-27 |
| **Objective** | Add a pre-commit gate that prevents `test_*.py` files from being placed directly under `tests/unit/`, enforcing the sub-package mirroring convention at commit time |
| **Outcome** | ✅ Hook implemented, 13 unit tests added, full suite passes (3185/3185), PR #1122 merged |
| **PR** | HomericIntelligence/ProjectScylla#1122 |
| **Fixes** | Follow-up to #849 (manual quality audit), addresses #967 |

## Overview

`tests/unit/` must mirror the `scylla/` source tree (e.g. `scylla/metrics/` → `tests/unit/metrics/`).
Without enforcement, new test files sometimes land at `tests/unit/test_foo.py` instead of
`tests/unit/metrics/test_foo.py`, requiring a manual audit to catch.

This skill adds a Python-based pre-commit hook that rejects commits whenever a `test_*.py` file
exists directly under `tests/unit/` (depth 1). Only `__init__.py` and `conftest.py` are allowed
at that level.

## When to Use This Skill

Invoke when:

- A project enforces `tests/unit/<subpackage>/` mirroring of source packages
- A manual quality audit found loose test files at the root test level (follow-up after the fix)
- You want to prevent the same class of violation from recurring without relying on code review

## Verified Workflow

### Step 1 — Write the Checker Script

Create `scripts/check_unit_test_structure.py` following the same pattern as existing custom hooks
(`check_model_config_consistency.py`, `check_tier_config_consistency.py`):

```python
#!/usr/bin/env python3
"""Enforce tests/unit/ mirroring convention."""

import argparse
import sys
from pathlib import Path

ALLOWED_NAMES = {"__init__.py", "conftest.py"}


def find_violations(unit_root: Path) -> list[Path]:
    """Return sorted list of test_*.py files at depth 1 under unit_root."""
    return sorted(p for p in unit_root.glob("test_*.py") if p.name not in ALLOWED_NAMES)


def check_unit_test_structure(unit_root: Path) -> int:
    if not unit_root.is_dir():
        print(f"ERROR: Directory not found: {unit_root}", file=sys.stderr)
        return 1
    violations = find_violations(unit_root)
    if violations:
        print(
            "ERROR: test_*.py files found directly under tests/unit/.\n"
            "Move them into the appropriate sub-package (e.g. tests/unit/metrics/).\n"
            "Violation(s):",
            file=sys.stderr,
        )
        for p in violations:
            print(f"  {p}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce tests/unit/ mirroring convention")
    parser.add_argument("--unit-root", type=Path, default=Path("tests/unit"))
    args = parser.parse_args()
    return check_unit_test_structure(args.unit_root)


if __name__ == "__main__":
    sys.exit(main())
```

**Key design choices**:
- `glob("test_*.py")` — depth 1 only (does not recurse)
- `ALLOWED_NAMES` set for fast lookup
- `--unit-root` CLI argument for testability
- Returns 1 on violation (pre-commit convention)

### Step 2 — Write Unit Tests

Create `tests/unit/scripts/test_check_unit_test_structure.py`. Essential test cases:

| Test | Assertion |
|------|-----------|
| `test_returns_empty_for_clean_directory` | No `test_*.py` → empty list |
| `test_detects_test_file_at_root` | `test_foo.py` at root → violation |
| `test_ignores_allowed_names` | `__init__.py`, `conftest.py` → allowed |
| `test_ignores_test_files_in_subdirectory` | `tests/unit/metrics/test_foo.py` → OK |
| `test_returns_multiple_violations_sorted` | Results are sorted |
| `test_non_test_python_files_ignored` | `helper.py` → not a violation |
| `test_clean_directory_returns_zero` | Exit code 0 when clean |
| `test_violation_returns_one` | Exit code 1 on violation |
| `test_missing_directory_returns_one` | Non-existent dir → exit 1 |
| `test_violation_message_printed_to_stderr` | Error output to stderr |
| `test_subpackage_tests_pass` | Sub-package tests don't trigger |
| `test_allowed_files_pass[__init__.py]` | Parametrized |
| `test_allowed_files_pass[conftest.py]` | Parametrized |

### Step 3 — Register the Hook

In `.pre-commit-config.yaml`, add under the local Python hooks repo:

```yaml
- id: check-unit-test-structure
  name: Check Unit Test Structure
  description: Fails if any test_*.py file exists directly under tests/unit/ (enforces sub-package mirroring convention)
  entry: pixi run python scripts/check_unit_test_structure.py
  language: system
  files: ^tests/unit/.*\.py$
  pass_filenames: false
```

**`files:` pattern**: `^tests/unit/.*\.py$` triggers the hook only when Python files under
`tests/unit/` are staged — avoids running on every commit.

**`pass_filenames: false`**: The script scans the directory itself rather than receiving file
arguments (consistent with other structural validators in this project).

### Step 4 — Verify Against the Repo

```bash
pixi run python scripts/check_unit_test_structure.py
# Should exit 0 (no violations)
echo $?  # 0

pixi run python -m pytest tests/unit/scripts/test_check_unit_test_structure.py -v --no-cov
# 13 passed
```

### Step 5 — Run Full Suite and Push

```bash
pixi run python -m pytest tests/ --no-cov 2>&1 | tail -3
# N passed, N warnings

git add scripts/check_unit_test_structure.py \
        tests/unit/scripts/test_check_unit_test_structure.py \
        .pre-commit-config.yaml
git commit -m "feat(hooks): add pre-commit hook to enforce tests/unit/ mirroring convention"
git push -u origin <branch>
gh pr create --title "..." --body "Closes #967"
gh pr merge --auto --rebase
```

## Failed Attempts

### ❌ Running Full Suite from a Git Worktree Exposes Pre-existing Flaky Tests

**Context**: The pre-push hook runs `pixi run pytest -x` (stop at first failure). Three tests that
pass on `main` failed when run from inside a git worktree:

**1. `test_orchestrator.py::TestEvalOrchestratorEndToEnd::test_run_single_with_mocks`**

- **Root cause**: Mock patch targets `scylla.executor.workspace.checkout_hash` but `orchestrator.py`
  imports the name directly: `from scylla.executor import checkout_hash`. Python's mock system
  patches the **module-level binding**, not the already-imported reference. So `checkout_hash` in
  `orchestrator.py` was never mocked. On `main`, this accidentally worked because git in the tmp
  dir could find the commit hash via the parent repo's object store. In a worktree, the git
  context differs and `git checkout <hash>` in the tmp dir fails.

- **Fix**: Change patch target from `scylla.executor.workspace.checkout_hash` to
  `scylla.e2e.orchestrator.checkout_hash` (and same for `clone_repo`).

- **Rule**: Always patch at the **call site** (where the name is bound), not the definition site.
  When `module_a.py` does `from module_b import func`, patch `module_a.func`, NOT `module_b.func`.

**2. `test_run_report.py::TestGetWorkspaceFiles::test_git_error_returns_empty_list`**

- **Root cause**: Test created a bare tmp directory and expected `git ls-files` to fail (not a
  git repo). In a git worktree, any directory underneath the worktree inherits the parent repo's
  git context — so `git ls-files` succeeded and returned thousands of files.

- **Fix**: Mock `subprocess.run` to return `returncode=128` (simulate git error):
  ```python
  @patch("subprocess.run")
  def test_git_error_returns_empty_list(self, mock_run, tmp_path):
      mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="not a git repository")
      result = _get_workspace_files(tmp_path / "workspace")
      assert result == []
  ```

**3. `test_retry.py::TestRetryOnNetworkError::test_uses_longer_initial_delay`**

- **Root cause**: Test used wall-clock timing (`elapsed >= 2.0`) to verify a 2-second backoff.
  Under system load from the full test suite (3185 tests), the actual elapsed time was ~1.09s.

- **Fix**: Mock `time.sleep` and assert the correct delay value:
  ```python
  with patch("time.sleep") as mock_sleep:
      result = decorated()
      mock_sleep.assert_called_once_with(2.0)
  ```

- **Rule**: Never use wall-clock timing assertions in unit tests. Mock `time.sleep` and assert
  the correct argument instead.

## Results & Parameters

**Tests**: 3185 passed, 8 warnings, 78.36% coverage (threshold: 75%)

**Hook trigger**: `files: ^tests/unit/.*\.py$` — runs whenever unit test Python files are staged

**Allowed exceptions** (depth-1 files the hook permits): `__init__.py`, `conftest.py`

**Script location**: `scripts/check_unit_test_structure.py`
**Test location**: `tests/unit/scripts/test_check_unit_test_structure.py`

## Related Skills

- `move-loose-test-files` — How to fix violations the hook would catch (moving test_*.py to correct sub-packages)
- `pre-commit-maintenance` — General pre-commit hook management patterns
- `fix-ci-test-failures` — Broader CI failure diagnosis and repair
