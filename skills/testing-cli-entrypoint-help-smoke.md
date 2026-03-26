---
name: testing-cli-entrypoint-help-smoke
description: "Smoke-test Python CLI entry points with --help subprocess calls and import verification. Use when: (1) a package declares [project.scripts] entry points, (2) entry points need regression protection, (3) an issue asks for CLI importability tests."
category: testing
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - python
  - cli
  - integration-testing
  - entry-points
  - smoke-tests
---

# Testing CLI Entry Points with --help Smoke Tests

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Verify all `[project.scripts]` entry points are importable and respond to `--help` without crashing |
| **Outcome** | Success — 8 tests (4 import + 4 subprocess) all pass in 0.39s |
| **Verification** | verified-local |

## When to Use

- A Python package declares `[project.scripts]` entry points in `pyproject.toml`
- Entry points need smoke tests to catch import errors, missing dependencies, or broken `main()` signatures
- An issue explicitly asks for CLI entry point integration tests
- The existing integration tests only cover module imports, not the `main()` functions that serve as entry points

Do NOT use when:
- Entry points require real credentials or network access just for `--help` (check first)
- The package doesn't use argparse/click (custom CLI parsing may not support `--help`)

## Verified Workflow

### Quick Reference

```bash
# Run CLI entry point tests
pixi run pytest tests/integration/test_cli_entry_points.py -v --no-cov

# Verify a single entry point manually
python -m hephaestus.git.changelog --help
```

### Detailed Steps

#### 1. Read `pyproject.toml` to find entry points

```bash
grep -A10 '\[project.scripts\]' pyproject.toml
```

Example output:
```toml
[project.scripts]
hephaestus-changelog = "hephaestus.git.changelog:main"
hephaestus-merge-prs = "hephaestus.github.pr_merge:main"
hephaestus-system-info = "hephaestus.system.info:main"
hephaestus-download-dataset = "hephaestus.datasets.downloader:main"
```

#### 2. Verify each module has a `main()` function and `__main__` block

```bash
grep -n "def main\|if __name__" hephaestus/git/changelog.py
```

Confirm: each module has `def main()` and `if __name__ == "__main__": main()`.

#### 3. Check for side effects before `--help`

Read each `main()` function to verify `--help` exits cleanly:
- argparse handles `--help` **before** any business logic runs — `sys.exit(0)` is called by argparse
- This is safe as long as there are no module-level side effects (network calls, file writes) at import time

#### 4. Create the test file

Key design decisions:
- **Use `sys.executable -m module.path`** instead of installed script names — avoids depending on pip-installed entry points
- **Parametrize with ids** matching the script names from `pyproject.toml` for readable test output
- **Two test classes**: import verification (fast, in-process) + subprocess `--help` (realistic, out-of-process)
- **Assert usage text** in stdout to confirm argparse actually ran (not just a silent exit 0)

```python
import importlib
import subprocess
import sys
import pytest

ENTRY_POINTS = [
    ("hephaestus.git.changelog", "main"),
    ("hephaestus.github.pr_merge", "main"),
    ("hephaestus.system.info", "main"),
    ("hephaestus.datasets.downloader", "main"),
]

class TestCLIEntryPointImports:
    @pytest.mark.parametrize(
        "module_path,func_name",
        ENTRY_POINTS,
        ids=["hephaestus-changelog", "hephaestus-merge-prs",
             "hephaestus-system-info", "hephaestus-download-dataset"],
    )
    def test_main_importable_and_callable(self, module_path: str, func_name: str) -> None:
        mod = importlib.import_module(module_path)
        main_func = getattr(mod, func_name, None)
        assert main_func is not None, f"{module_path}.{func_name} not found"
        assert callable(main_func), f"{module_path}.{func_name} is not callable"

class TestCLIEntryPointHelp:
    @pytest.mark.parametrize(
        "module_path",
        [ep[0] for ep in ENTRY_POINTS],
        ids=["hephaestus-changelog", "hephaestus-merge-prs",
             "hephaestus-system-info", "hephaestus-download-dataset"],
    )
    def test_help_exits_cleanly(self, module_path: str) -> None:
        result = subprocess.run(
            [sys.executable, "-m", module_path, "--help"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, (
            f"{module_path} --help exited with code {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "usage:" in result.stdout.lower(), (
            f"{module_path} --help did not produce usage text"
        )
```

#### 5. Run and verify

```bash
pixi run pytest tests/integration/test_cli_entry_points.py -v --no-cov
pixi run ruff check tests/integration/test_cli_entry_points.py
pixi run ruff format --check tests/integration/test_cli_entry_points.py
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Using installed script names | Tried `subprocess.run(["hephaestus-changelog", "--help"])` | Requires package to be pip-installed with entry points registered; fails in pixi/dev environments | Use `sys.executable -m module.path` — tests the same `main()` code path via `__main__` block without needing pip install |
| N/A — direct approach worked | Import + subprocess two-pronged strategy succeeded on first try | N/A | For argparse-based CLIs, `--help` is always safe — argparse calls `sys.exit(0)` before any business logic |

## Results & Parameters

**Test file**: `tests/integration/test_cli_entry_points.py`

**Test count**: 8 (4 import + 4 subprocess)

**Execution time**: ~0.39s total

**Pattern for adding new entry points**: Add a tuple to `ENTRY_POINTS` list and a corresponding id string to both `ids=` lists.

**Key assertion**: Always check for `"usage:"` in stdout — this confirms argparse actually ran, not just a silent exit 0 from some other code path.

**Pre-flight check for new entry points**: Before adding to tests, verify:
1. Module has `def main()` function
2. Module has `if __name__ == "__main__": main()` block
3. `main()` uses argparse (or click) with `--help` support
4. No module-level side effects that would crash on import

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #52, PR #95 | 4 CLI entry points: changelog, merge-prs, system-info, download-dataset |
