---
name: ci-pytest-pip-install-pyproject-addopts-trap
description: "Slim `pip install pytest` CI jobs silently inherit `addopts` from `pyproject.toml` and fail because pytest-cov (or other plugins in addopts) is not installed. Use when: (1) a matrix CI job does `pip install pytest` without the full project env and crashes with 'unrecognized arguments: --cov=...' or 'no module named yaml', (2) a lightweight test job works locally but fails in CI with missing plugin errors, (3) splitting a pixi/poetry test job into a minimal pip-only job starts failing after addopts was set in pyproject.toml."
category: ci-cd
date: 2026-05-09
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - pytest
  - pip-install
  - addopts
  - pyproject-toml
  - pytest-cov
  - pyyaml
  - ci-matrix
  - pixi
---

# CI pytest `pip install` Trap: `addopts` Inherited from `pyproject.toml`

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-09 |
| **Objective** | Document the failure mode where a slim `pip install pytest` CI job crashes because `pyproject.toml` injects `--cov=...` or other plugin flags into every pytest invocation |
| **Outcome** | Identified and fixed in HomericIntelligence/ProjectArgus PRs #289 and #273 |
| **Verification** | verified-ci |

## When to Use

- A CI job does `pip install pytest` (or a minimal subset) and crashes with `unrecognized arguments: --cov=<module>` or `ERROR: unrecognized arguments: --cov-report=xml`
- A matrix job that previously worked starts failing after `[tool.pytest.ini_options] addopts = "--cov=..."` was added to `pyproject.toml`
- A test job fails with `ModuleNotFoundError: No module named 'yaml'` when using `pip install pytest` without the project environment
- Splitting a pixi/poetry-based test step into a lighter CI job that installs only `pytest`
- Deciding whether to install `pytest-cov` and `pyyaml` in a pip-only CI job vs. using the full project environment

## Verified Workflow

### Quick Reference

```yaml
# Option A (quickest fix) — install all required test deps explicitly
- name: Test exporter
  run: |
    pip install pytest pytest-cov pyyaml
    pytest tests/test_exporter.py

# Option B — override addopts inline to disable inherited flags
- name: Test exporter
  run: |
    pip install pytest
    pytest -o addopts= tests/test_exporter.py

# Option C (most robust) — use the project's real environment
- name: Test exporter
  run: pixi run pytest tests/test_exporter.py
```

### Detailed Steps

1. **Identify the failure mode**: Check CI logs for either:
   - `ERRORS ... unrecognized arguments: --cov=<module>` — pytest-cov is missing from the pip install line
   - `ModuleNotFoundError: No module named 'yaml'` — pyyaml is missing

2. **Locate the `addopts` setting** in `pyproject.toml`:
   ```toml
   [tool.pytest.ini_options]
   addopts = "--cov=exporter --cov-report=xml"
   ```
   These flags are injected into **every** pytest invocation, including slim CI jobs that didn't install `pytest-cov`.

3. **Choose a fix pattern**:

   **Option A — Add all missing deps to the `pip install` line** (quickest, good when the job must stay pip-only):
   ```yaml
   pip install pytest pytest-cov pyyaml
   ```
   Add `pyyaml` if any test file does `import yaml`. Add any other missing plugins similarly.

   **Option B — Disable `addopts` for this specific invocation** (good when you intentionally don't want coverage in this job):
   ```yaml
   pytest -o addopts= tests/test_exporter.py
   ```
   Warning: this silently disables coverage collection, which may bypass the project's coverage intent.

   **Option C — Use the project's actual environment** (most robust, zero dep-drift):
   ```yaml
   run: pixi run pytest tests/test_exporter.py
   # or: poetry run pytest tests/test_exporter.py
   ```
   This inherits all real deps and stays in sync with `pyproject.toml` automatically.

4. **Verify the fix** by re-running the CI job and confirming it exits 0.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Attempt 1 | `pip install pytest pytest-cov` without `pyyaml` | Tests imported `yaml`; `ModuleNotFoundError: No module named 'yaml'` | `pip install pytest pytest-cov` doesn't pull in pyyaml; must list it explicitly |
| Attempt 2 | `pip install pytest` alone | `pyproject.toml` has `addopts = "--cov=..."` which pytest passes to pytest-cov; pytest-cov not installed → `unrecognized arguments` | `addopts` is read regardless of which environment invokes pytest |
| Attempt 3 | Removing `--cov` from pytest CLI but keeping `addopts` in `pyproject.toml` | `addopts` overrides CLI; flags re-injected automatically | Must either override `addopts=` at invocation time or remove from `pyproject.toml` |

## Results & Parameters

Verified in HomericIntelligence/ProjectArgus on 2026-05-09:
- PRs #273 and #289 both hit this trap in the "Test exporter" CI job
- Root cause: `[tool.pytest.ini_options] addopts = "--cov=exporter --cov-report=xml"` in `pyproject.toml`
- Fix applied: `pip install pytest pytest-cov pyyaml` (Option A)
- Result: CI green after adding `pyyaml`

**Decision guide**:

| Situation | Recommended Fix |
|-----------|----------------|
| Job must stay pip-only and needs coverage | Option A: add all missing deps |
| Job intentionally skips coverage | Option B: `-o addopts=` |
| Job can use pixi/poetry | Option C: `pixi run pytest` (always prefer) |
| `addopts` will keep accumulating deps | Consider Option C to avoid dep-drift |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectArgus | CI "Test exporter" matrix job — PRs #273 and #289 (2026-05-09) | `pyyaml` missing from `pip install pytest pytest-cov`; fixed by adding it |
