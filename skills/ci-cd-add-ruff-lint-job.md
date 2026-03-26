---
name: ci-cd-add-ruff-lint-job
description: "Add ruff lint and format check as a separate parallel CI job. Use when: (1) ruff config exists in pyproject.toml but CI doesn't enforce it, (2) pre-commit hooks can be bypassed, (3) adding lint enforcement to an existing test workflow."
category: ci-cd
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [ruff, linting, ci, github-actions, pixi]
---

# Add Ruff Lint Job to CI Workflow

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Add ruff lint and format checks to CI so violations are caught before merge, even when pre-commit hooks are bypassed |
| **Outcome** | Successful — separate lint job added to test.yml, runs in parallel with test matrix |
| **Verification** | verified-local |

## When to Use

- Repository has ruff rules in `pyproject.toml` but no CI enforcement
- Pre-commit hooks exist for ruff but can be bypassed with `--no-verify`
- Adding lint enforcement to an existing GitHub Actions test workflow
- Want lint and tests to run in parallel for faster CI feedback

## Verified Workflow

### Quick Reference

```bash
# Verify codebase passes locally before modifying CI
pixi run ruff check hephaestus scripts tests
pixi run ruff format --check hephaestus scripts tests

# Validate workflow YAML after editing
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/test.yml')); print('OK')"
```

### Detailed Steps

1. **Verify codebase passes lint locally** — run both `ruff check` and `ruff format --check` on all source directories before touching CI. If the codebase has violations, fix them first in a separate commit.

2. **Add a separate `lint` job** to the existing test workflow (e.g., `test.yml`). Use a separate job rather than a step in the test job so it runs in parallel and has clear failure attribution.

3. **Use a shorter timeout** for the lint job (10 minutes vs 30 for tests) since lint is fast.

4. **Add workflow-level hardening** if not already present:
   - `concurrency` group with `cancel-in-progress: true`
   - `permissions: contents: read` (least privilege)

5. **Lint job template** (pixi-based projects):

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.head_ref || github.sha }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@v6

      - name: Install pixi
        uses: prefix-dev/setup-pixi@v0.9.4
        with:
          pixi-version: v0.63.2

      - name: Cache pixi environments
        uses: actions/cache@v5
        with:
          path: |
            .pixi
            ~/.cache/rattler/cache
          key: pixi-${{ runner.os }}-${{ hashFiles('pixi.lock') }}
          restore-keys: |
            pixi-${{ runner.os }}-

      - name: Lint check
        run: pixi run ruff check hephaestus scripts tests

      - name: Format check
        run: pixi run ruff format --check hephaestus scripts tests
```

6. **Validate YAML** — parse the workflow file with Python's `yaml.safe_load()` before committing.

7. **Lint job doesn't need `setup-python`** — pixi manages the Python environment, so skip `actions/setup-python` in the lint job (unlike the test job which may need it for matrix Python versions).

8. **Cache key for lint job omits python-version** — since there's no matrix, use a simpler cache key: `pixi-${{ runner.os }}-${{ hashFiles('pixi.lock') }}`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Adding lint as a step in the test job | Considered adding ruff as a step inside the existing test matrix job | Would run redundantly for each matrix entry (unit + integration × each OS) and couples lint to test job failures | Use a separate job for lint — runs once, in parallel, with independent failure reporting |

## Results & Parameters

### Directories to Lint

Match the directories in `pixi.toml` lint/format tasks:

```bash
# Standard HomericIntelligence pattern
pixi run ruff check hephaestus scripts tests
pixi run ruff format --check hephaestus scripts tests
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Separate job (not step) | Parallel execution, clearer failure attribution |
| Same workflow file | Keeps CI consolidated — no workflow sprawl |
| 10-minute timeout | Lint is fast; 30 minutes is wasteful |
| No `setup-python` | Pixi manages Python; redundant with `setup-pixi` |
| Simpler cache key | No matrix dimensions to vary |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #56, PR #105 | Added lint job to `test.yml`, verified locally, CI pending |
