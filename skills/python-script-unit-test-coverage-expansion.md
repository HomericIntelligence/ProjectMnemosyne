---
name: python-script-unit-test-coverage-expansion
description: "Use when: (1) a Python script in scripts/ has zero test coverage and needs
  tests added; (2) a coverage threshold audit reveals that scripts/ is under-tested
  vs. the threshold; (3) a follow-up issue requests tests for specific untested modules;
  (4) you need to close CLI command-handler test gaps (cmd_run/cmd_repair style);
  (5) you need to audit existing tests before writing new ones to avoid duplication."
category: testing
date: 2026-05-19
version: "1.0.0"
user-invocable: false
history: python-script-unit-test-coverage-expansion.history
tags:
  - python
  - pytest
  - unit-tests
  - coverage
  - mocking
  - scripts
---
# python-script-unit-test-coverage-expansion

## Overview

| Item | Details |
| ------ | --------- |
| Theme | Systematically adding mock-based unit tests to previously untested Python scripts and source modules |
| Language | Python / pytest |
| Patterns | Class-grouped tests, sys.path.insert import, tmp_path fixtures, mock-only subprocess/filesystem |
| Proven Result | Raised scripts/ test coverage from 29% to 65% (10/34 → 22/34 scripts) across multiple sessions |

## When to Use

1. A Python script in `scripts/` has been identified as having zero test coverage
2. A coverage threshold audit reveals the scripts/ folder is under-tested
3. A follow-up GitHub issue requests tests for specific public functions or modules
4. You need to close CLI command-handler test gaps (e.g., cmd_run/cmd_repair patterns)
5. You are about to write tests and need to audit what already exists to avoid duplication
6. You need to retrofit tests onto existing code without modifying the script itself

**Trigger phrases**:
- "X% of scripts lack unit tests"
- "add tests for the remaining untested scripts"
- "script test coverage audit"
- "follow-up to close the test gap"
- "tests only cover argument parsing, not what the command actually does"

## Verified Workflow

### Quick Reference

```bash
# Step 0: Audit first — always grep before writing
grep -rn "def test_" tests/unit/scripts/ --include="*.py" | wc -l
ls scripts/*.py | grep -v __init__ | wc -l

# Step 1: Run existing tests to establish baseline
python3 -m pytest tests/unit/scripts/ -v --tb=short

# Step 2: Import pattern (preferred — no path manipulation when pythonpath configured)
# If pyproject.toml has: pythonpath = [".", "scripts"]
from my_script import func_a, func_b

# Step 3: Fallback sys.path.insert (when pythonpath not configured)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from my_script import func_a, func_b

# Step 4: Run tests directly (NOT via pixi — too slow for iteration)
python3 -m pytest tests/unit/scripts/test_my_script.py -v

# Step 5: Final validation via package manager
<package-manager> run python -m pytest tests/unit/scripts/ -v
```

### Step 1: Audit Before Writing

**Always search before writing a single test.** This avoids duplicating 8+ existing tests.

```bash
# Find all test files covering the target script
grep -rl "my_script\|MyClass" tests/ --include="*.py"

# Count existing tests per file
grep -c "def test_" tests/unit/scripts/test_my_script.py

# List test classes to identify coverage gaps
grep -n "^class Test" tests/unit/scripts/test_my_script.py
```

Build a coverage matrix before writing:

| Requirement | Covered? | Test function | File |
| ------------- | ---------- | --------------- | ------ |
| Happy path | ✅ | `test_happy_path` | `test_my_script.py:45` |
| Missing file | ❌ | — | — |
| Empty input | ❌ | — | — |

### Step 2: Check pyproject.toml for pythonpath

```toml
[tool.pytest.ini_options]
pythonpath = [".", "scripts"]
```

When present, this allows:
- `from generate_changelog import parse_commit` (top-level scripts)
- `from agents.agent_utils import AgentInfo` (sub-packages)
- `from scripts.check_unit_test_structure import find_violations` (full path)

If not present, use `sys.path.insert` at the top of the test file.

### Step 3: Read the Script Before Writing Tests

Read each script fully to find:
1. Pure functions with no side effects (test directly, no mocking needed)
2. Functions that call `subprocess.run` (mock `<module>.subprocess.run`)
3. `main()` functions controlled by argparse (mock `sys.argv`)
4. Module-level constants that affect behavior (mock with `patch("<module>._REPO_ROOT", ...)`)
5. Class-based designs (instantiate in a fixture, test each method)

Use quick `python3 -c` one-liners to verify assumptions before encoding them as assertions:

```bash
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from my_script import parse_frontmatter
fm, rest = parse_frontmatter('---\nname: foo\n---\nBody')
print('fm:', fm)
print('rest:', repr(rest))
"
```

### Step 4: Rank by Testability × Impact (for bulk expansion)

Score each untested script and test highest-ROI targets first:

| Axis | High (3) | Medium (2) | Low (1) |
| ------ | ---------- | ----------- | --------- |
| **Testability** | Pure functions, no subprocess | Some mocking needed | Subprocess-heavy, no helpers |
| **Impact** | Entry point / pre-commit hook | Frequently invoked | Rarely used utility |

Highest scores get tested first. Minimum viable target = half the total scripts.

### Step 5: Choose the Mock-Only Pattern by Script Type

**Pure Functions (easiest — no mocking needed)**:

```python
from fix_table_underscores import fix_table_underscores

def test_escapes_bare_underscore():
    content = "column_name & value\n"
    result = fix_table_underscores(content)
    assert r"column\_name" in result
```

**Subprocess-Heavy Scripts (mock at module level)**:

```python
from unittest.mock import MagicMock, patch

def test_successful_merge_returns_true():
    mock_result = MagicMock()
    mock_result.returncode = 0
    with patch("merge_prs.subprocess.run", return_value=mock_result):
        result = merge_pr(42)
    assert result is True
```

For **sequential subprocess calls**, use `side_effect` with a list:

```python
with patch("get_stats.subprocess.run", side_effect=[mock_total, mock_open_result]):
    result = get_issues_stats("2026-01-01", "2026-01-31", None, "owner/repo")
```

**Filesystem-Heavy Scripts (use tmp_path fixture)**:

```python
def test_detects_violation_in_file(tmp_path: Path) -> None:
    f = tmp_path / "test.py"
    f.write_text("Result = DomainResult\n")
    violations = detect_shadowing(f)
    assert len(violations) == 1
```

**Class-Based Scripts (instantiate and test methods)**:

```python
@pytest.fixture
def fixer():
    return MarkdownFixer(dry_run=True)

class TestMarkdownFixer:
    def test_dry_run_does_not_write(self, fixer, tmp_path):
        md = tmp_path / "test.md"
        original = "# Heading:\n\n\ncontent\n"
        md.write_text(original)
        fixer.fix_file(md)
        assert md.read_text() == original  # unchanged
```

**Module-Level Constants**:

```python
with patch("check_defaults_filename._REPO_ROOT", tmp_path):
    result = main()
```

The patched tmp_path must replicate the exact subdirectory structure the function expects.

### Step 6: Standard Test File Template

```python
"""Tests for scripts/<script_name>.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from <script_name> import <function_to_test>


class Test<FunctionName>:
    """Tests for <function_name>()."""

    def test_happy_path(self, tmp_path: Path) -> None:
        """<Description of what passes>."""
        # Arrange, Act, Assert

    def test_error_case(self) -> None:
        """<Description of error path>."""
        ...
```

Key conventions:
- `from __future__ import annotations` always first
- Class-based test grouping (one class per function/feature)
- Docstrings on every test method
- `tmp_path` fixture for filesystem operations
- `pytest.CaptureFixture[str]` (not `object`) for capsys

### Step 7: Dynamic Loader (for module-level patching)

```python
import importlib.util

SCRIPT_PATH = Path(__file__).parent.parent.parent / "scripts" / "my_script.py"

def load_module():
    spec = importlib.util.spec_from_file_location("my_script", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

@pytest.fixture
def mod():
    return load_module()
```

Use `unittest.mock.patch.object(mod, "GLOBAL_CONSTANT", fake_value)` to override
module-level constants (e.g., hardcoded paths) in tests.

### Step 8: CLI Handler Gap Pattern (cmd_run / cmd_repair)

When an existing test file covers parser tests but not the actual command handlers:

1. Identify correct patch path — must match `from ... import` inside the handler:

   ```python
   # In manage_experiment.py cmd_run():
   from scylla.e2e.runner import run_experiment   # patch: "scylla.e2e.runner.run_experiment"
   ```

2. Capture config passed to mocked function via closure:

   ```python
   captured_configs: list[Any] = []

   def mock_run_experiment(config, tiers_dir, results_dir, fresh):
       captured_configs.append(config)
       return {"T0": {}}

   with patch("scylla.e2e.runner.run_experiment", side_effect=mock_run_experiment):
       result = cmd_run(args)

   assert captured_configs[0].tiers_to_run == [TierID.T0, TierID.T2]
   ```

3. Use `--skip-judge-validation` flag to eliminate additional mock requirements.

4. Test exception-continue path with invalid JSON:

   ```python
   (run_dir / "run_result.json").write_text("{ not valid json }")
   result = cmd_repair(args)
   assert result == 0   # Must not crash
   ```

### Step 9: Agent Subdirectory Scripts

If the repo has `scripts/agents/*.py`, create a parallel subdirectory:

```
tests/unit/scripts/agents/__init__.py
tests/unit/scripts/agents/test_agent_utils.py
tests/unit/scripts/agents/test_validate_agents.py
```

The `__init__.py` is required for pytest discovery.

### Step 10: Run, Fix Pre-commit, Commit

```bash
# Run only new tests first (fast iteration)
python3 -m pytest tests/unit/scripts/test_my_script.py -v

# Run full suite before committing
<package-manager> run python -m pytest tests/unit/scripts/ -v

# Pre-commit auto-fixes ruff formatting — re-stage and re-commit
git add tests/scripts/test_my_script.py
git commit -m "test(scripts): add unit tests for my_script.py"
```

Common pre-commit issues to fix before second attempt:
- **F841 unused variables** — remove `as mock_fh` when you don't assert on it
- **var-annotated** — add type annotation: `config: dict[str, object] = {}`
- **capsys type** — use `pytest.CaptureFixture[str]` not `object`
- **E501 docstrings** — keep docstrings ≤100 chars

### Step 11: Count and Report Coverage

```
Tested scripts before: N
Tested scripts after:  N+K
Total scripts:         M
Coverage:              (N+K)/M * 100%
Goal met:              YES / NO
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Running tests via `pixi run python -m pytest` | Used pixi for test execution during development | Command timed out (>2 min env activation) | Use `python3 -m pytest` directly for fast iteration; only use pixi for final validation |
| Running background pytest task | Launched pytest as a background task to avoid blocking | Output file was empty for minutes | Background tasks don't stream output — run pytest synchronously in foreground |
| Importing unused constant in tests | Imported `SKILL_CATEGORY_OVERRIDE` for documentation but never asserted on it | Ruff auto-removed it, causing first commit to fail | Only import symbols you actually use in assertions; ruff-check runs in pre-commit |
| Extending file without reading it | Attempted to write new test classes without reading existing file content | Edit tool rejected the change (file not read first) | Always read the target file before any edit — required by tool policy |
| Writing tests immediately without audit | Started drafting test functions before searching | Would have duplicated 8+ existing tests | Always grep for existing tests first |
| Single-file search | Only searched one test file | Missed additional tests in sibling test file | Search all files in `tests/` recursively |
| Trusting issue title | Assumed "add tests" meant tests were missing | All required cases already existed | Issue wording "add any missing cases" implies audit first |
| Wrong patch path for imported functions | Patched `<package>.automation.curses_ui.restore_terminal` | Module does `from scylla.utils.terminal import restore_terminal` inline | Patch at the definition site: `scylla.utils.terminal.restore_terminal` |
| Mocking multiprocessing.Manager | Attempted to mock the Manager for RateLimitCoordinator tests | Mock didn't replicate the event/dict semantics correctly | Use a real `Manager()` in a `with Manager() as mgr:` context |
| Thread timing test without state setup | Called `ui.start()` twice without controlling thread state | Thread completed before second call due to mocked curses.wrapper | Set `ui.running = True` and `ui.thread` manually to simulate already-running state |
| Global subprocess mock | Used `patch("subprocess.run", ...)` | Mock was at stdlib level; module had its own import binding | Always patch at module level: `patch("<module_name>.subprocess.run", ...)` |

## Results & Parameters

### Verified Coverage Outcomes

| Session | Before | After | New Tests | Files |
| --------- | -------- | ------- | ----------- | ------- |
| ProjectScylla #1162 | 10/34 (29%) | 22/34 (65%) | 453 | 13 |
| ProjectScylla #1358 | 22/34 (65%) | 34/34 (100%) | 130 | 12 |
| ProjectScylla #850 | ~73% | 74.93% | 106 | 5 |
| ProjectScylla #1113 | 114 tests | 119 tests | 5 | 1 (extended) |

### pyproject.toml pytest Configuration

```toml
[tool.pytest.ini_options]
pythonpath = [".", "scripts"]
```

### Parametrize Pattern for Mapping Tables

```python
@pytest.mark.parametrize("commit_type,category", [
    ("feat", "Features"),
    ("fix", "Bug Fixes"),
    ("perf", "Performance"),
])
def test_type_to_category_mapping(self, commit_type, category):
    result = categorize_commits([f"abc|{commit_type}: msg|Author"])
    assert category in result
```

### Registry/Dispatch Dict Test (no side effects)

```python
from generate_figures import FIGURES

class TestFiguresRegistry:
    def test_figures_functions_are_callable(self) -> None:
        for name, (_category, fn) in FIGURES.items():
            assert callable(fn)
```

### RateLimitCoordinator Safe Test Pattern

```python
def test_signal_rate_limit_sets_pause(self) -> None:
    with Manager() as mgr:
        coordinator = RateLimitCoordinator(mgr)
        # Pre-set resume so check_if_paused doesn't block
        coordinator._resume_event.set()
        coordinator.signal_rate_limit(info)
        assert coordinator._pause_event.is_set()
```

### Coverage Comment (when all cases already exist)

```python
# ============================================================================
# Test __hash__
# Coverage (issue #NNNN):
#   (1) identical tensors produce equal hashes      -> test_hash_immutable
#   (2) different shape produces different hash     -> test_hash_different_shapes_differ
# ============================================================================
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Issue #1162, PR #1343 — scripts/ 29% → 65% | extend-script-test-coverage |
| ProjectScylla | Issue #1358, PR #1383 — 12 additional scripts | script-unit-test-coverage |
| ProjectScylla | Issue #850, PR #975 — source modules 74.93% | unit-tests-untested-modules |
| ProjectScylla | Issue #1113 — cmd\_run/cmd\_repair gap | close-script-test-gap-cmd-run-repair |
| ProjectMnemosyne | Issue #3309, PR #3927 — migrate\_odyssey\_skills.py | add-unit-tests-for-existing-script |
| ProjectOdyssey | Issue #4051, PR #4859 — hash coverage audit | test-coverage-audit |
