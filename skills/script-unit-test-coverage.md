---
name: script-unit-test-coverage
description: 'TRIGGER CONDITIONS: Use when adding unit tests for scripts/ that lack
  test files, following the ProjectScylla pattern of mocked I/O with pytest class-based
  tests.'
category: testing
date: 2026-03-03
version: 1.0.0
user-invocable: false
---
# script-unit-test-coverage

How to systematically add unit test coverage for Python scripts that use subprocess, file I/O, and complex external dependencies, using mocking to keep tests fast and hermetic.

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-03-03 |
| Objective | Add tests for 12 untested scripts in scripts/ (40% coverage gap) |
| Outcome | Success — 130 new tests across 12 files, all passing, pre-commit clean |

## When to Use

- You need to add tests for scripts that call `subprocess.run`, touch the filesystem, or import heavy scylla modules
- You have scripts with `main()` functions and argparse CLI arguments that need validation
- You need to mock module-level constants like `_REPO_ROOT` or `_SCRIPT_DIR` that are set at import time
- You want to test a registry/dispatch dict (like `FIGURES`) without invoking any heavy dependencies

## Verified Workflow

### Step 1 — Understand the script's testable surface

Read each script to find:
1. Pure functions with no side effects (test directly, no mocking needed)
2. Functions that call `subprocess.run` (mock `<module>.subprocess.run`)
3. `main()` functions controlled by `argparse` (mock `sys.argv`)
4. Module-level constants that affect behavior (mock with `patch("<module>._REPO_ROOT", ...)`)

### Step 2 — Follow the ProjectScylla test file pattern

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

### Step 3 — Patch module-level constants correctly

When a script sets `_REPO_ROOT = Path(__file__).parent.parent` at module level,
patch it as a module attribute:

```python
with patch("check_defaults_filename._REPO_ROOT", tmp_path):
    result = main()
```

The patched tmp_path must replicate the exact subdirectory structure the function
expects. For `config/defaults.yaml`, create:

```python
config_dir = tmp_path / "config"
config_dir.mkdir()
(config_dir / "defaults.yaml").write_text("key: value\n")
```

### Step 4 — Mock subprocess.run with side_effect for sequential calls

When a function makes multiple subprocess calls, use `side_effect` with a list:

```python
mock_total = MagicMock()
mock_total.returncode = 0
mock_total.stdout = "10\n"

mock_open_result = MagicMock()
mock_open_result.returncode = 0
mock_open_result.stdout = "3\n"

with patch("get_stats.subprocess.run", side_effect=[mock_total, mock_open_result]):
    result = get_issues_stats("2026-01-01", "2026-01-31", None, "owner/repo")
```

### Step 5 — Test registry/dispatch dicts directly

For scripts that expose a module-level registry dict (e.g., `FIGURES`), test the
dict structure without calling any generators:

```python
from generate_figures import FIGURES

class TestFiguresRegistry:
    def test_figures_functions_are_callable(self) -> None:
        for name, (_category, fn) in FIGURES.items():
            assert callable(fn)
```

### Step 6 — Run and fix pre-commit issues

Pre-commit will apply ruff formatting automatically on first fail. Re-stage
and re-commit. Common issues to fix before the second attempt:

1. **F841 unused variables** — Remove `as mock_fh` from `with patch(...)` when you don't assert on the mock
2. **var-annotated** — Add type annotation for dicts assigned to plain `config = {}` variables: `config: dict[str, object] = {}`
3. **capsys type** — Use `pytest.CaptureFixture[str]` not `object` as the capsys parameter type

### Step 7 — Verify all tests pass

```bash
pixi run python -m pytest tests/unit/scripts/ -v
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

**Test counts by script:**

| Script | Tests | Key technique |
| -------- | ------- | --------------- |
| `check_defaults_filename.py` | 4 | patch `_REPO_ROOT`, `validate_defaults_filename` |
| `docker_build_timing.py` | 13 | Pure functions — no mocking needed |
| `export_data.py` | 8 | patch `shapiro_wilk`; pandas DataFrame in tests |
| `generate_all_results.py` | 7 | patch `subprocess.run` + `terminal_guard` + `sys.argv` |
| `generate_figures.py` | 7 | FIGURES registry structural checks only |
| `generate_tables.py` | 3 | patch all 10 table generators + `load_all_experiments` |
| `get_stats.py` | 6 | `side_effect=[mock1, mock2]` for sequential subprocess calls |
| `implement_issues.py` | 7 | `parse_args` + `setup_logging` with `sys.argv` mock |
| `lint_configs.py` | 14 | `ConfigLinter` class methods tested directly |
| `migrate_skills_to_mnemosyne.py` | 14 | Pure utility functions tested directly |
| `plan_issues.py` | 10 | `parse_args` + `main()` return codes with `Planner` mock |
| `validation.py` | 17 | Filesystem functions + regex helpers with `tmp_path` |

**pyproject.toml pytest config (important for imports):**
```toml
[tool.pytest.ini_options]
pythonpath = [".", "scripts"]
```
This allows `from <script_name> import ...` without any path manipulation.

**Total: 130 tests, all passing**

## Verified On

- ProjectScylla (Python 3.10+, pytest, pixi environment)
- 12 scripts covered in one session
- Pre-commit: ruff, mypy, black all pass
