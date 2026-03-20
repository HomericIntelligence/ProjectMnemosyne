---
name: doc-config-drift-check
description: Add a lightweight CI pre-commit script to detect drift between documented
  metric values (CLAUDE.md, README.md) and authoritative pyproject.toml config sources.
category: ci-cd
date: 2026-02-28
version: 1.0.0
user-invocable: false
---
# Skill: doc-config-drift-check

## Overview

| Field     | Value |
|-----------|-------|
| Date      | 2026-02-28 |
| Issue     | #1151 |
| PR        | #1225 |
| Objective | Add a pre-commit gate that detects when documented metric values (coverage %, --cov path) diverge from the authoritative values in `pyproject.toml` |
| Outcome   | Success — `scripts/check_doc_config_consistency.py` with 26 unit tests; wired as pre-commit hook |

## When to Use

- You have numeric thresholds or config paths documented in markdown files (CLAUDE.md, README.md) that must stay in sync with authoritative config (pyproject.toml)
- A manual audit has already caught documentation staleness at least once and you want to automate detection
- You want a hard gate (exit 1) rather than a warning for doc/config drift
- The project follows the `scripts/check_*.py` + pre-commit hook pattern already established in the codebase

## Root Cause Pattern

Documentation values (e.g., "75%+ test coverage") drift from the authoritative source (pyproject.toml `fail_under = 75`) silently over time. Manual audits catch these only periodically. A lightweight grep-based script that reads the authoritative value and asserts the docs match provides a continuous enforcement gate.

## Verified Workflow

### 1. Identify the drift candidates

```bash
# Find authoritative value in pyproject.toml
grep -n "fail_under\|addopts\|cov" pyproject.toml

# Find documented values in CLAUDE.md
grep -n "coverage\|test coverage" CLAUDE.md

# Find --cov= references in README.md
grep -n "\-\-cov" README.md
```

### 2. Create the enforcement script

Place at `scripts/check_doc_config_consistency.py`:

```python
#!/usr/bin/env python3
"""Enforce consistency between documentation metric values and authoritative config sources."""

import argparse
import re
import sys
import tomllib
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def load_pyproject_coverage_threshold(repo_root: Path) -> int:
    """Read fail_under from [tool.coverage.report] in pyproject.toml."""
    pyproject = repo_root / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)
    return int(data["tool"]["coverage"]["report"]["fail_under"])


def extract_cov_path_from_pyproject(repo_root: Path) -> str:
    """Read --cov=<path> value from [tool.pytest.ini_options].addopts."""
    pyproject = repo_root / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)
    addopts = data["tool"]["pytest"]["ini_options"]["addopts"]
    if isinstance(addopts, str):
        addopts = addopts.split()
    for item in addopts:
        m = re.match(r"^--cov=(.+)$", item)
        if m:
            return m.group(1)
    sys.exit(1)


def check_claude_md_threshold(repo_root: Path, expected_threshold: int) -> list[str]:
    """Check that CLAUDE.md documents the correct coverage threshold."""
    text = (repo_root / "CLAUDE.md").read_text(encoding="utf-8")
    matches = re.findall(r"(\d+)%\+?\s+test coverage", text)
    errors = []
    for raw in matches:
        if int(raw) != expected_threshold:
            errors.append(f"CLAUDE.md: {raw}% != {expected_threshold}% (pyproject.toml)")
    return errors


def check_readme_cov_path(repo_root: Path, expected_path: str) -> list[str]:
    """Check that all --cov=<path> occurrences in README.md match expected_path."""
    text = (repo_root / "README.md").read_text(encoding="utf-8")
    errors = []
    for path in re.findall(r"--cov=(\S+)", text):
        if path != expected_path:
            errors.append(f"README.md: --cov={path} != --cov={expected_path} (pyproject.toml)")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=_REPO_ROOT)
    args = parser.parse_args()
    repo_root = args.repo_root

    errors = []
    threshold = load_pyproject_coverage_threshold(repo_root)
    errors.extend(check_claude_md_threshold(repo_root, threshold))
    cov_path = extract_cov_path_from_pyproject(repo_root)
    errors.extend(check_readme_cov_path(repo_root, cov_path))

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### 3. Write unit tests

Place at `tests/unit/scripts/test_check_doc_config_consistency.py`.

Key test patterns:
- Use `tmp_path` fixture to write synthetic `pyproject.toml`, `CLAUDE.md`, `README.md`
- Test happy path, each mismatch variant, missing files, missing keys
- For `main()` integration tests: mutate `sys.argv` and call `main()` directly — it returns `int`, so `assert result == 0/1` (do NOT use `pytest.raises(SystemExit)` unless `main()` calls `sys.exit()` internally)

```python
def test_all_matching_exits_zero(self, tmp_path: Path) -> None:
    from scripts.check_doc_config_consistency import main
    import sys
    repo = self._make_repo(tmp_path)
    original_argv = sys.argv
    sys.argv = ["check_doc_config_consistency.py", "--repo-root", str(repo)]
    try:
        result = main()
        assert result == 0
    finally:
        sys.argv = original_argv
```

### 4. Wire pre-commit hook

In `.pre-commit-config.yaml` (after `audit-doc-policy`):

```yaml
- id: check-doc-config-consistency
  name: Check Doc/Config Metric Consistency
  description: Fails if coverage threshold in CLAUDE.md or README.md --cov path diverges from pyproject.toml
  entry: pixi run python scripts/check_doc_config_consistency.py
  language: system
  files: ^(CLAUDE\.md|README\.md|pyproject\.toml)$
  pass_filenames: false
```

### 5. Verify

```bash
# Run unit tests only
pixi run python -m pytest tests/unit/scripts/test_check_doc_config_consistency.py -v --no-cov

# Run script directly against real repo
pixi run python scripts/check_doc_config_consistency.py --verbose

# Run full suite
pixi run python -m pytest tests/ -v
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Script location | `scripts/check_doc_config_consistency.py` |
| Test location | `tests/unit/scripts/test_check_doc_config_consistency.py` |
| Test count | 26 (all passing) |
| Hook ID | `check-doc-config-consistency` |
| Hook trigger | `^(CLAUDE\.md|README\.md|pyproject\.toml)$` |
| stdlib used | `tomllib` (Python 3.11+), `re`, `argparse` |
| Commit message | `feat(ci): add pre-commit check for doc/config metric drift` |
| Exit codes | 0 = all pass, 1 = any violation |
| Pattern matched in CLAUDE.md | `(\d+)%\+?\s+test coverage` |
| Pattern matched in README.md | `--cov=(\S+)` |

## Key Insights

1. **tomllib is stdlib from Python 3.11+** — use it directly without adding a dependency. For Python 3.10 projects that have `tomllib` available via pixi environment, it still imports fine.

2. **`main()` should return int, not call `sys.exit()`** — the `if __name__ == "__main__"` block handles `sys.exit(main())`. This makes unit-testing `main()` straightforward: call it directly and assert the return value.

3. **`README.md` with no `--cov=` occurrences is a pass** — absence of a claim is not a violation. Only validate what is explicitly stated.

4. **Pre-commit hook file scope** — use `^(CLAUDE\.md|README\.md|pyproject\.toml)$` as the `files:` pattern so the hook only fires when these specific files change, not on every commit.

5. **The "sys.argv mutation" pattern for integration tests** — save `sys.argv`, mutate it to pass `--repo-root`, call `main()`, restore in `finally`. This avoids subprocess overhead while still testing the argument-parsing path.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1151, PR #1225 | [notes.md](../../references/notes.md) |
