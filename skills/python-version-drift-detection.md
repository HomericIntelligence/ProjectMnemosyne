---
name: python-version-drift-detection
description: Detect Python version drift between pyproject.toml classifiers and Dockerfile
  FROM line. Use when adding CI checks to prevent silent version mismatches.
category: ci-cd
date: '2026-03-19'
version: 1.0.0
mcp_fallback: none
tier: 2
---
# Python Version Drift Detection

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-02 |
| Objective | Add CI check to detect when `pyproject.toml` Python classifiers and `Dockerfile FROM python:X.Y` diverge silently |
| Outcome | Operational — PR #1292 merged into ProjectScylla |

## When to Use

- Adding a new Python version classifier to `pyproject.toml` without updating the Dockerfile
- Bumping the Dockerfile base image without updating classifiers
- Setting up CI for any project that has both `pyproject.toml` classifiers and a Python Dockerfile
- Pre-commit hook that guards `pyproject.toml` or `docker/Dockerfile` changes

## Verified Workflow

### 1. Create the check script (`scripts/check_python_version_consistency.py`)

Key design decisions:
- **stdlib-only**: Use `tomllib` (Python 3.11+) with `tomli` fallback for 3.10 — no extra dependencies
- **Numeric version comparison**: `(3, 9) < (3, 10)` not string sort (`"3.9" > "3.10"` is wrong)
- **Regex for Dockerfile**: `^\s*FROM\s+python:(\d+\.\d+)` with `re.IGNORECASE | re.MULTILINE`
  — handles `FROM python:3.12-slim`, `FROM python:3.12-slim@sha256:...`, `FROM python:3.12 AS builder`
- **Exits 1 on missing/malformed files**: Don't silently pass when inputs are absent
- **Compares highest classifier to Dockerfile**: Not just any classifier — the highest X.Y

```python
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

_DOCKERFILE_FROM_RE = re.compile(r"^\s*FROM\s+python:(\d+\.\d+)", re.IGNORECASE | re.MULTILINE)
_CLASSIFIER_VERSION_RE = re.compile(r"Programming Language :: Python :: (\d+\.\d+)$")
```

### 2. Add pre-commit hook (`.pre-commit-config.yaml`)

```yaml
- id: check-python-version-consistency
  name: Check Python Version Consistency
  description: Fails if pyproject.toml Python classifiers and Dockerfile FROM version differ
  entry: pixi run python scripts/check_python_version_consistency.py
  language: system
  files: ^(pyproject\.toml|docker/Dockerfile)$
  pass_filenames: false
```

### 3. Add CI step (`.github/workflows/test.yml`)

Place **before** `Install pixi` so it uses the runner's system Python (stdlib-only check, no pixi needed):

```yaml
- name: Check Python version consistency (pyproject.toml vs Dockerfile)
  run: python3 scripts/check_python_version_consistency.py
```

### 4. Write unit tests (31 tests across 3 classes)

- `TestGetHighestPythonClassifier`: 9 tests — missing file, malformed TOML, no classifiers, numeric comparison (3.9 < 3.10)
- `TestGetDockerfilePythonVersion`: 13 tests — slim/alpine variants, digest-pinned, multi-stage, case-insensitive
- `TestCheckVersionConsistency`: 9 tests — match/mismatch, verbose output, missing files

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

**Script invocation:**

```bash
# Check consistency (exit 0 = match, exit 1 = mismatch or parse error)
python3 scripts/check_python_version_consistency.py

# With verbose output showing parsed versions
python3 scripts/check_python_version_consistency.py --verbose

# Custom repo root
python3 scripts/check_python_version_consistency.py --repo-root /path/to/repo
```

**Expected paths (relative to repo root):**
- `pyproject.toml` — standard PEP 517 project file
- `docker/Dockerfile` — Dockerfile in `docker/` subdirectory

**Regex patterns used:**

```python
# FROM line: captures X.Y from any python:X.Y variant
r"^\s*FROM\s+python:(\d+\.\d+)"  # flags: IGNORECASE | MULTILINE

# Classifier line: captures X.Y from Programming Language :: Python :: X.Y
r"Programming Language :: Python :: (\d+\.\d+)$"
```

**Test counts:** 31 new tests; 3615 total project tests passed after integration.

## References

- ProjectScylla issue #1168 (follow-up from #1118 Python version standardization)
- ProjectScylla PR #1292
- See `scripts/check_model_config_consistency.py` for similar pattern (filename vs field consistency)
