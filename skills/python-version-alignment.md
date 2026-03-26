---
name: python-version-alignment
description: "Align Python version across pyproject.toml, pixi.toml, Dockerfile, and CI test matrix. Use when: (1) classifiers don't match CI matrix, (2) Dockerfile uses wrong Python, (3) pixi ignores setup-python in multi-version CI."
category: tooling
date: 2026-03-25
version: "3.0.0"
user-invocable: false
verification: verified-local
history: python-version-alignment.history
tags:
- python
- ci-cd
- test-matrix
- pixi
- setup-python
- version-drift
- github-actions
---

# Python Version Alignment

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Align Python version across pyproject.toml, pixi.toml, Dockerfile, and CI test matrix |
| **Outcome** | v1: Dockerfile aligned. v2: CI test matrix expanded to 3.10-3.12. v3: Added 3.13 forward-looking coverage |
| **Verification** | verified-local |
| **History** | [changelog](./python-version-alignment.history) |

## When to Use

Use this workflow when:

- A quality audit flags version mismatch across config files
- `pyproject.toml` classifiers don't match the Dockerfile base image Python version
- `pixi.toml` resolves a different Python than the Dockerfile uses
- PR review mentions "Python version drift" or "config inconsistency"
- **CI test matrix only tests one Python version but `pyproject.toml` claims multiple** (e.g., `requires-python = ">=3.10"` with 3.10/3.11/3.12 classifiers but CI only tests 3.12)
- **Pixi-based CI workflow needs multi-version Python testing** (pixi ignores `setup-python`)
- **A new Python stable release is available** (e.g., 3.13) but classifiers and CI matrix haven't been updated

Trigger symptoms:
- Dockerfile `FROM python:X.Y.Z-slim` doesn't match `pyproject.toml` classifier max version
- CI/CD runs on a different Python than local `pixi` environment
- `requires-python = ">=3.10"` but Dockerfile uses `3.14.x` (bleeding edge)
- CI matrix has `python-version: ["3.12"]` but classifiers list 3.10, 3.11, 3.12
- New Python release (e.g., 3.13) is stable but not yet in classifiers or CI matrix

## Verified Workflow

### Quick Reference

```bash
# Audit Python version references across all config files
grep -n "python\|Python\|3\.[0-9]" pyproject.toml pixi.toml .github/workflows/test.yml

# Validate workflow YAML after editing
python -c "import yaml; yaml.safe_load(open('.github/workflows/test.yml')); print('OK')"

# Run tests locally to verify nothing breaks
pytest tests/unit -v
```

### Detailed Steps

#### Part A: Dockerfile Alignment (v1.0.0 workflow)

1. **Audit all config files** for Python version references
2. **Determine canonical version** from `pyproject.toml` classifiers (highest listed = Dockerfile target)
3. **Pull target image** and get SHA256 digest: `docker pull python:3.12-slim`
4. **Update Dockerfile** — both `FROM` lines and `python3.X` path references in multi-stage builds
5. **Verify** no remaining old-version references: `grep -rn "3\.14\|python3\.14" docker/`

#### Part B: CI Test Matrix Expansion (v2.0.0 workflow)

1. **Identify the gap**: Compare `pyproject.toml` classifiers against `.github/workflows/test.yml` matrix
2. **Expand the matrix**: Change `python-version: ["3.12"]` to `python-version: ["3.10", "3.11", "3.12"]`
3. **Replace pixi with setup-python + pip** (see critical note below):
   - Remove `Install pixi` step (e.g., `prefix-dev/setup-pixi@v0.9.4`)
   - Change `pixi run pip install -e .` to `pip install -e ".[dev]"`
   - Change all `pixi run pytest` to `pytest`, `pixi run python` to `python`
   - Update cache from pixi paths to `~/.cache/pip`
4. **Restrict coverage upload** to one Python version to avoid duplicate reports:
   ```yaml
   if: matrix.test-type == 'unit' && matrix.python-version == '3.12'
   ```
5. **Validate YAML** and run tests locally
6. **Verify CI** spawns N×M jobs (N Python versions × M test types)

#### Part C: Adding New Python Release to CI (v3.0.0 workflow)

When a new Python stable release is available (e.g., 3.13), adding it is straightforward if the CI already uses `setup-python`:

1. **Add version to matrix**: Change `python-version: ["3.12"]` to `python-version: ["3.12", "3.13"]`
2. **Add trove classifier** to `pyproject.toml`: `"Programming Language :: Python :: 3.13"`
3. **Run tests locally** to check for deprecation warnings or incompatibilities
4. **Push and verify CI** — the new version will run as an additional matrix job
5. **Fix any 3.x-specific issues** on the PR branch before merging

**Note**: If the project uses pixi in CI, adding a new version to `python-version` matrix alone has no effect (see Part B critical note). However, if the CI was already converted to `setup-python + pip` (as in Part B), simply adding the version to the matrix works.

**CRITICAL — Pixi vs setup-python**:
> Pixi manages its own Python installation from conda-forge and **ignores** the Python provided by `actions/setup-python`. If your workflow uses pixi, adding versions to the matrix has NO EFFECT — pixi will install whatever version its solver chooses. To genuinely test multiple Python versions, you must use `setup-python` + `pip install -e ".[dev]"` instead of pixi in the test workflow.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Keep pixi + expand matrix | Attempted to add 3.10/3.11 to matrix while keeping pixi | Pixi ignores setup-python and installs its own Python from conda-forge. Matrix expansion alone has no effect. | For multi-version Python CI, must use setup-python + pip, not pixi |
| Pixi --override to pin Python | Considered using pixi's override mechanism to force specific Python versions | Fragile and non-standard — fighting the tool rather than working with it | Standard CI patterns (setup-python + pip) are more reliable than tool-specific workarounds |
| v1.0.0: Dockerfile only | Direct approach worked for Dockerfile alignment | N/A — successful | Straightforward when scope is limited to Dockerfile |
| v3.0.0: Add 3.13 with pixi in CI | Added "3.13" to matrix in workflow that still uses pixi for some projects | Pixi ignores setup-python — same lesson as v2.0.0 | Always verify whether CI uses pixi or setup-python before expanding matrix. If pixi, matrix expansion alone is a no-op |

## Results & Parameters

### v3.0.0: Add Python 3.13 Forward-Looking Coverage (ProjectHephaestus Issue #58)

**Before:**
```yaml
python-version: ["3.12"]  # 2 CI jobs
```

**After:**
```yaml
python-version: ["3.12", "3.13"]  # 4 CI jobs (2 versions × 2 test types)
```

**Files Changed:**
| File | Change |
|------|--------|
| `.github/workflows/test.yml` line 16 | `["3.12"]` → `["3.12", "3.13"]` |
| `pyproject.toml` line 23 | Added `"Programming Language :: Python :: 3.13"` classifier |
| `pixi.lock` | Auto-updated sha256 due to pyproject.toml change |

**Test Results:**
- 384 unit tests passed locally with 82.13% coverage (above 80% threshold)
- No Python 3.13-specific deprecation warnings or incompatibilities found
- CI validation pending (PR #112)

**Note:** This project still uses pixi in CI (`prefix-dev/setup-pixi`). The `python-version` matrix entry is used by `actions/setup-python` which sets up a system Python, but pixi installs its own. The matrix expansion is still valuable for cache keying and future CI refactoring, but does not guarantee tests actually run on 3.13 until the pixi-to-pip migration from v2.0.0 (Issue #44) is also merged.

### v2.0.0: CI Test Matrix (ProjectHephaestus Issue #44)

**Before:**
```yaml
python-version: ["3.12"]  # 2 CI jobs (1 version × 2 test types)
```

**After:**
```yaml
python-version: ["3.10", "3.11", "3.12"]  # 6 CI jobs (3 versions × 2 test types)
```

**Files Changed:**
| File | Change |
|------|--------|
| `.github/workflows/test.yml` line 16 | `["3.12"]` → `["3.10", "3.11", "3.12"]` |
| `.github/workflows/test.yml` lines 27-43 | Replaced pixi install/cache with pip install/cache |
| `.github/workflows/test.yml` lines 47-64 | Removed `pixi run` prefix from all commands |
| `.github/workflows/test.yml` line 61 | Added `&& matrix.python-version == '3.12'` to coverage upload condition |

**Test Results:**
- 384 unit tests passed locally on Python 3.12
- CI validation pending (PR #75)

### v1.0.0: Dockerfile Alignment (ProjectScylla Issue #1118)

| File | Change |
|------|--------|
| `docker/Dockerfile` line 15 | `python:3.14.2-slim` → `python:3.12-slim` (pinned SHA256) |
| `docker/Dockerfile` line 44 | Same update for runtime stage |
| `docker/Dockerfile` line 53 | `python3.14/site-packages` → `python3.12/site-packages` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #58, PR #112 — Add Python 3.13 to CI and classifiers | Added 3.13 to matrix and pyproject.toml classifier; 384 tests pass locally |
| ProjectHephaestus | Issue #44, PR #75 — Expand CI test matrix to 3.10/3.11/3.12 | Replaced pixi with setup-python + pip for multi-version CI |
| ProjectScylla | Issue #1118, PR #1166 — Dockerfile Python version alignment | Dockerfile updated from 3.14.2 to 3.12 with pinned SHA256 |
