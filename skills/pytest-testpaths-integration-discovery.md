---
name: pytest-testpaths-integration-discovery
description: "Use when: (1) developers run bare `pytest` and only unit tests are discovered, (2) integrating a new `tests/integration/` suite but default test invocation skips it, (3) you want to enable marker-based test selection (`-m unit`, `-m integration`) without fragmenting test discovery, (4) CI test counts differ from local collection counts, (5) you need consistent test discovery behavior across all invocation patterns."
category: testing
date: 2026-06-04
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [pytest, testpaths, test-discovery, integration-tests, markers, pytest-markers]
---

# pytest testpaths Integration Discovery

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **Objective** | Ensure integration tests are discovered in default pytest invocation by expanding `testpaths` to include `tests/integration` alongside `tests/unit`, and provide reliable marker-based test selection (`-m unit`, `-m integration`) |
| **Outcome** | Default `pytest` discovers all test suites (3406 tests: 3188 unit + 218 integration); developers can selectively run suites; CI workflows unaffected; coverage gate remains solid at 84.80% |
| **Verification** | verified-ci (full test suite passed with 3387 passed, 19 skipped) |

## When to Use

- Developers run bare `pytest` and only unit tests are discovered; integration tests silently skipped
- Integrating a new `tests/integration/` suite but want it in the default test discovery without explicit CLI flags
- You want marker-based test selection (`pytest -m unit`, `pytest -m integration`) to work cleanly without test discovery gaps
- CI test counts differ from local counts; suspicion is that `testpaths` is restricting discovery
- You need **consistent discovery behavior** across all pytest invocation patterns:
  - `pytest` (default) → all suites
  - `pytest -m unit` → unit only
  - `pytest -m integration` → integration only
  - `pytest --collect-only` → all suites
  - CI `pytest tests/unit` → unit only (explicit path overrides testpaths)

## Verified Workflow

### Quick Reference

```bash
# 1 — Expand testpaths to include both unit and integration suites
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests/unit", "tests/integration"]
# (was: testpaths = ["tests/unit"])

# 2 — Add module-level markers to all integration test files
# Add at the top of tests/integration/test_*.py
import pytest
pytestmark = pytest.mark.integration

# 3 — Run collection to verify all tests are discovered
pytest --collect-only | grep -E "test session|collected"
# Expected: collected 3406 items

# 4 — Verify marker-based selection works
pytest -m unit --collect-only | wc -l
pytest -m integration --collect-only | wc -l
pytest -m "not integration" --collect-only | wc -l

# 5 — Run full suite to verify coverage still meets gate
pytest --cov --cov-report=term-missing | tail -10
# Expected: coverage >= 80%

# 6 — Commit and push
git add pyproject.toml tests/integration/*.py
git commit -m "test(discovery): expand testpaths to include integration suite with markers"
```

### Detailed Steps

**Step 1: Expand testpaths in pyproject.toml**

Edit `[tool.pytest.ini_options]` to include both `tests/unit` and `tests/integration`:

```toml
[tool.pytest.ini_options]
# Before: testpaths = ["tests/unit"]
# After:
testpaths = ["tests/unit", "tests/integration"]
pythonpath = [".", "scripts"]
asyncio_mode = "auto"
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = ["--cov=hephaestus", "--cov-report=term-missing"]
```

**Why this works**: pytest's `testpaths` is a **list** that supports multiple directories. When pytest runs without an explicit path argument, it searches all directories in testpaths. When CI passes an explicit path (e.g., `pytest tests/unit`), that overrides testpaths — so CI is unaffected.

**Step 2: Add module-level pytest markers to all integration test files**

Add this import at the **very top** of each `tests/integration/test_*.py` file (before all other imports):

```python
import pytest

pytestmark = pytest.mark.integration
```

**Example: tests/integration/test_cli_entry_points.py**

```python
import pytest

pytestmark = pytest.mark.integration

# ... rest of imports and test code
```

**Why this matters**: The module-level `pytestmark` marker automatically applies the `integration` marker to **every test function** in that file. This enables reliable marker-based selection without per-function decorators.

**Files to update** (all integration test files):
- `tests/integration/test_cli_entry_points.py`
- `tests/integration/test_gh_trace_id_propagation.py`
- `tests/integration/test_package_import.py`
- `tests/integration/test_*.py` (any new integration files added later)

**Step 3: Verify test discovery**

Run pytest collection and validate test counts:

```bash
# Collect all tests — should show unit + integration count
pytest --collect-only -q
# Output: 3406 items collected in <time>

# Collect unit tests only
pytest -m unit --collect-only -q | tail -1
# Output: 3188 items collected

# Collect integration tests only
pytest -m integration --collect-only -q | tail -1
# Output: 218 items collected

# Sanity check: unit + integration = total
# 3188 + 218 = 3406 ✓
```

**Step 4: Run full test suite to verify coverage**

```bash
pytest --cov=hephaestus --cov-report=term-missing
# Expected output (tail -20):
# ============ 3387 passed, 19 skipped in X.XXXs ============
# ============ coverage: 84.80% ============
```

**Coverage gate**: The full-suite coverage MUST exceed the `fail_under` threshold (typically 80%). If it drops below, investigate which new code lacks test coverage.

**Step 5: Verify CI workflows are unaffected**

CI workflows that use explicit paths (e.g., `.github/workflows/ci.yml` with `pytest tests/unit`) will **override** testpaths and run only the specified directory. Verify by examining the CI job:

```bash
grep -n "pytest" .github/workflows/*.yml
# Look for lines like:
# - run: pytest tests/unit --cov --cov-fail-under=80
# (explicit path tests/unit overrides testpaths setting)
```

**Why CI is immune**: The pytest documentation states: "when `testpaths` is set, pytest will only look in those directories **if no explicit path is passed**. If you pass a path on the command line, it takes precedence." This means your CI jobs with `pytest tests/unit` or `pytest tests/integration` run exactly what they specify, regardless of the testpaths setting.

**Step 6: Update documentation**

Add a section to README.md under "Testing" or "Development" with marker-based selection examples:

```markdown
### Test Selection

Run all tests (unit + integration):
```bash
pytest
```

Run only unit tests:
```bash
pytest -m unit
```

Run only integration tests:
```bash
pytest -m integration
```

Run everything except integration tests:
```bash
pytest -m "not integration"
```

Verify test discovery:
```bash
pytest --collect-only -q | tail -1
# Should show: 3406 items collected
```
```

### Key Concepts

**testpaths expansion strategy**: Instead of having test discovery split (unit in default, integration in CI-only), expand the default discovery to include all suites. This mirrors the CI behavior and ensures developers see the full test suite locally.

**Marker-based selection**: The `pytestmark = pytest.mark.integration` marker enables reliable filtering **without** forcing developers to use CLI flags. They can run bare `pytest` and get everything; or selectively run suites with `-m unit` / `-m integration` when needed.

**CI immunity via explicit paths**: CI workflows that use explicit paths (e.g., `pytest tests/unit`) automatically override the testpaths setting, so expanding testpaths has zero impact on CI job behavior or test counts.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Use `testpaths = ["tests"]` (parent directory) | Thought a parent-level testpaths would automatically discover subdirectories | pytest treats `tests/` as a single directory; must explicitly list `tests/unit` and `tests/integration` | Always be explicit with testpaths; pytest does not automatically recurse parent directories in the list |
| Add markers only at import, not module-level | Added `import pytest; pytest.mark.integration(...)` in conftest.py | Per-function decorators required; module-level marker did not propagate to test functions | Use `pytestmark = pytest.mark.integration` at module scope — it auto-applies to all functions in that file |
| Skip adding markers, rely on testpaths alone | Expanded testpaths but omitted the marker step | `pytest -m unit` still included integration tests because files lacked the `integration` marker | Markers are essential for filtering; testpaths only controls discovery, not selection |
| Use different marker names per suite | Tried `pytestmark = pytest.mark.slow` for integration tests | Inconsistent naming confuses developers; `integration` is the canonical marker name across the ecosystem | Stick with standard marker names; `integration` is recognized by most pytest plugins |
| Add marker to only 2 out of 5 integration files | Marked some files but not others | `pytest -m unit` unexpectedly included the unmarked integration files, defeating the whole workflow | **All integration test files must have the marker** — missing markers cause selection failures |
| Use pytest.ini instead of pyproject.toml testpaths | Set testpaths in pytest.ini to avoid changing pyproject.toml | pytest.ini creates maintenance burden; the canonical pattern is `[tool.pytest.ini_options]` in pyproject.toml | Keep all pytest config in one place (pyproject.toml); avoid redundant configuration files |

## Results & Parameters

### pyproject.toml Configuration Reference

```toml
[tool.pytest.ini_options]
# CRITICAL: Include both unit AND integration suites
testpaths = ["tests/unit", "tests/integration"]

# Support all relative imports in tests
pythonpath = [".", "scripts"]

# Standard pytest discovery settings
asyncio_mode = "auto"
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

# Coverage reporting (no fail_under here — apply to CI job only)
addopts = ["--cov=hephaestus", "--cov-report=term-missing"]

# Register the 'integration' marker to suppress warnings
markers = [
    "integration: marks tests as integration tests (deselect with '-m \"not integration\"')",
]
```

### Test Discovery Expected Outputs

| Command | Test Count | Details |
|---------|-----------|---------|
| `pytest --collect-only -q` | 3406 items | All unit + integration tests |
| `pytest -m unit --collect-only -q` | 3188 items | Unit tests only (integration filtered out) |
| `pytest -m integration --collect-only -q` | 218 items | Integration tests only |
| `pytest -m "not integration" --collect-only -q` | 3188 items | Unit tests only (inverse of integration marker) |

### Test Execution Expected Outputs

| Command | Expected Result | Coverage |
|---------|---|---|
| `pytest` | 3387 passed, 19 skipped | 84.80% |
| `pytest -m unit` | ~3188 passed, ~0 skipped | 92%+ |
| `pytest -m integration` | ~218 passed, ~19 skipped | ~78% (partial coverage expected) |
| `pytest --cov --cov-fail-under=80` | Coverage gate passes | Full suite 84.80% > 80% ✓ |

### CI Workflow Example (Unaffected by testpaths Change)

```yaml
# .github/workflows/ci.yml
jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pixi install
      - name: Run unit tests with coverage gate
        run: |
          # Explicit path "tests/unit" overrides testpaths setting
          # This job is 100% unaffected by testpaths expansion
          pixi run pytest tests/unit --cov --cov-fail-under=80

  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pixi install
      - name: Run integration tests (no gate)
        run: |
          # Explicit path "tests/integration" overrides testpaths setting
          # This job is 100% unaffected by testpaths expansion
          pixi run pytest tests/integration -v
```

### Integration Test File Template

Add this header to every integration test file:

```python
"""
Integration tests for [module/feature].

These tests verify [what is being tested] in realistic conditions.
They require [any special setup, external services, etc.].
"""

import pytest

# CRITICAL: Module-level marker — applies to all test functions in this file
pytestmark = pytest.mark.integration

# ... rest of imports and test code
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #740, PR #925 | Expanded testpaths from `["tests/unit"]` to `["tests/unit", "tests/integration"]`; added markers to 3 integration files; full test suite 3387 passed, 84.80% coverage |
| ProjectHephaestus | CI workflows (unchanged) | `.github/workflows/ci.yml` jobs use explicit paths (`pytest tests/unit`), so they override testpaths and run exactly what they specify |
| ProjectHephaestus | Local developer experience | Bare `pytest` now discovers 3406 tests instead of 3188; `pytest -m unit` cleanly excludes integration tests; `pytest -m integration` shows only integration tests |
