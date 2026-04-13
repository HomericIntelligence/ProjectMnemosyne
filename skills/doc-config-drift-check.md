---
name: doc-config-drift-check
description: Add a lightweight CI pre-commit script to detect drift between documented
  metric values (CLAUDE.md, README.md) and authoritative pyproject.toml config sources,
  including coverage threshold, --cov path, and README test count claims.
category: ci-cd
date: 2026-02-28
version: 2.0.0
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
- README.md contains test count badges/mentions that may drift as tests are added

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


def collect_actual_test_count(repo_root: Path) -> int | None:
    """Run pytest --collect-only -q and return the number of collected tests."""
    import subprocess
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return None

    output = result.stdout + result.stderr
    # Match "N selected" or "N tests collected" or "N test collected"
    m = re.search(r"(\d+)\s+(?:tests?\s+)?(?:selected|collected)", output)
    if m:
        return int(m.group(1))
    return None


def check_readme_test_count(
    repo_root: Path, actual_count: int, tolerance: float = 0.10
) -> list[str]:
    """Check that test count claims in README.md are within tolerance of actual_count."""
    readme = repo_root / "README.md"
    if not readme.exists():
        return [f"README.md not found at {readme}"]

    text = readme.read_text(encoding="utf-8")
    raw_matches = re.findall(r"(\d[\d,]*)\+?\s+tests?", text, re.IGNORECASE)

    if not raw_matches:
        return ["README.md: No test count mention found (expected pattern: '<N> tests')"]

    errors: list[str] = []
    for raw in raw_matches:
        doc_count = int(raw.replace(",", ""))
        if abs(doc_count - actual_count) / actual_count > tolerance:
            errors.append(
                f"README.md: Test count mismatch — "
                f"README.md says {doc_count}, actual pytest count is {actual_count} "
                f"(tolerance: {int(tolerance * 100)}%)"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=_REPO_ROOT)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    repo_root = args.repo_root

    errors = []

    # Check 1: CLAUDE.md coverage threshold
    threshold = load_pyproject_coverage_threshold(repo_root)
    errors.extend(check_claude_md_threshold(repo_root, threshold))

    # Check 2: README.md --cov path
    cov_path = extract_cov_path_from_pyproject(repo_root)
    errors.extend(check_readme_cov_path(repo_root, cov_path))

    # Check 4: README.md test count
    actual_count = collect_actual_test_count(repo_root)
    if actual_count is None:
        if args.verbose:
            print("SKIP: Could not collect actual test count (pytest unavailable)")
    else:
        count_errors = check_readme_test_count(repo_root, actual_count)
        if count_errors:
            errors.extend(count_errors)
        elif args.verbose:
            print(f"PASS: README.md test count is within 10% of actual ({actual_count})")

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

#### TestCollectActualTestCount patterns

```python
from unittest.mock import MagicMock, patch

class TestCollectActualTestCount:
    def test_parses_n_tests_collected_line(self, tmp_path):
        mock_result = MagicMock()
        mock_result.stdout = "100 tests collected\n"
        mock_result.stderr = ""
        with patch(
            "scripts.check_doc_config_consistency.subprocess.run",
            return_value=mock_result,
        ):
            assert collect_actual_test_count(tmp_path) == 100

    def test_returns_none_on_subprocess_failure(self, tmp_path):
        with patch(
            "scripts.check_doc_config_consistency.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            assert collect_actual_test_count(tmp_path) is None
```

**Key design decision**: Patch `subprocess.run` in the script's own module namespace
(`scripts.check_doc_config_consistency.subprocess.run`), not `subprocess.run` globally.

#### TestCheckReadmeTestCount patterns

```python
class TestCheckReadmeTestCount:
    def test_within_tolerance_no_errors(self, tmp_path):
        # README says 3500, actual is 3507 → within 10%
        ...

    def test_outside_tolerance_returns_error(self, tmp_path):
        # README says 2000, actual is 3500 → >10%, error returned
        ...
```

#### Mock pattern for integration tests

When adding Check 4 to `main()`, all existing integration tests that call `main()` will
now run Check 4. Mock `collect_actual_test_count` so they don't spawn real pytest:

```python
with patch(
    "scripts.check_doc_config_consistency.collect_actual_test_count",
    return_value=3507,
):
    result = main()
    assert result == 0
```

Also update `_make_repo()` to accept `readme_test_count: int | None = 3500` so the
generated README contains a test count mention.

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
| N/A (Checks 1-3) | Direct approach worked | N/A | Solution was straightforward |
| Patch `subprocess.run` globally | `patch("subprocess.run", ...)` in test for `collect_actual_test_count` | Script already imported `subprocess`; patching the stdlib location has no effect on the already-imported reference | Always patch in the module's own namespace: `scripts.check_doc_config_consistency.subprocess.run` |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Script location | `scripts/check_doc_config_consistency.py` |
| Test location | `tests/unit/scripts/test_check_doc_config_consistency.py` |
| Test count (after Check 4) | 53 (26 original + 20 new + updates) |
| Hook ID | `check-doc-config-consistency` |
| Hook trigger | `^(CLAUDE\.md|README\.md|pyproject\.toml)$` |
| stdlib used | `tomllib` (Python 3.11+), `re`, `argparse`, `subprocess` |
| Exit codes | 0 = all pass, 1 = any violation |
| Pattern matched in CLAUDE.md | `(\d+)%\+?\s+test coverage` |
| Pattern matched in README.md (cov) | `--cov=(\S+)` |
| Pattern matched in README.md (test count) | `(\d[\d,]*)\+?\s+tests?` |
| Test count tolerance | 10% |

### Files Modified

| File | Changes |
|------|---------|
| `scripts/check_doc_config_consistency.py` | Original 3 checks (Issue #1151 / PR #1225) |
| `scripts/check_doc_config_consistency.py` | Added `import subprocess`, `collect_actual_test_count()`, `check_readme_test_count()`, Check 4 in `main()` (Issue #1226 / PR #1315) |
| `tests/unit/scripts/test_check_doc_config_consistency.py` | Added `TestCollectActualTestCount` (6 tests), `TestCheckReadmeTestCount` (8 tests), updated 5 integration tests to mock `collect_actual_test_count`, added 2 new integration tests |

### Tolerance Rationale

10% tolerance (`tolerance=0.10`) balances:
- **Too strict (0%)**: Every test addition breaks CI immediately
- **Too loose (50%)**: Allows numbers to drift significantly before catching
- **10%**: ~350 test gap on a 3500-test suite — roughly a sprint's worth of new tests

### Regex Pattern Breakdown (test count)

```python
r"(\d[\d,]*)\+?\s+tests?"
```

| Component | Matches |
|-----------|---------|
| `(\d[\d,]*)` | `3172`, `3,500`, `1` (commas allowed after first digit) |
| `\+?` | Optional `+` suffix (e.g. `3,500+`) |
| `\s+` | One or more spaces |
| `tests?` | `tests` or `test` (singular/plural) |

## Key Insights

1. **tomllib is stdlib from Python 3.11+** — use it directly without adding a dependency. For Python 3.10 projects that have `tomllib` available via pixi environment, it still imports fine.

2. **`main()` should return int, not call `sys.exit()`** — the `if __name__ == "__main__"` block handles `sys.exit(main())`. This makes unit-testing `main()` straightforward: call it directly and assert the return value.

3. **`README.md` with no `--cov=` occurrences is a pass** — absence of a claim is not a violation. Only validate what is explicitly stated.

4. **Pre-commit hook file scope** — use `^(CLAUDE\.md|README\.md|pyproject\.toml)$` as the `files:` pattern so the hook only fires when these specific files change, not on every commit.

5. **The "sys.argv mutation" pattern for integration tests** — save `sys.argv`, mutate it to pass `--repo-root`, call `main()`, restore in `finally`. This avoids subprocess overhead while still testing the argument-parsing path.

6. **`collect_actual_test_count` returns `int | None`** — `None` means skip (no hard failure for pytest being unavailable). Only fail when pytest is reachable and the documented count is out of range.

7. **Merges stdout + stderr before parsing** — pytest may write the summary line to either stream depending on version and verbosity settings.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #1151, PR #1225 — Checks 1-3 (coverage threshold + cov path) | [notes.md](../../references/notes.md) |
| ProjectScylla | Issue #1226, PR #1315 — Check 4 (test count validation) | [notes.md](../../references/notes.md) |
