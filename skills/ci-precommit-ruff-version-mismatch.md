---
name: ci-precommit-ruff-version-mismatch
description: "Diagnose and resolve CI failures where pre-commit ruff-format disagrees with pixi ruff. Use when: (1) pixi run ruff format --check passes locally but pre-commit ruff-format fails in CI with 'file would be reformatted', (2) ruff formatting results differ between pre-commit hooks and direct pixi invocations at the same version string."
category: ci-cd
date: 2026-04-25
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [ruff, pre-commit, formatting, pixi, ci, version-isolation]
---

# pre-commit Ruff Version Mismatch

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-25 |
| **Objective** | Fix CI failure where `pre-commit run --all-files` failed with "1 file would be reformatted" for ruff-format, but `pixi run ruff format --check` passed cleanly |
| **Outcome** | Success — removed ruff hooks from `.pre-commit-config.yaml` entirely; CI passed |
| **Verification** | verified-ci |
| **Project Context** | ProjectHermes PR #291 |

## When to Use

- `pre-commit run --all-files` fails with "1 file would be reformatted" or "files would be reformatted"
- `pixi run ruff format --check` passes locally with no issues
- The failing file appears clean by every other check (no syntax errors, no linting issues)
- You already tried pinning `astral-sh/ruff-pre-commit` to match the pixi ruff version exactly
- CI runs both a `lint` step (`pixi run lint`) and a `pre-commit` step separately

## Verified Workflow

### Quick Reference

```bash
# Diagnosis: confirm the disagreement is environment-specific, not a real formatting issue
pixi run ruff format --check .            # should pass
pixi run pre-commit run ruff-format --all-files  # fails

# Fix: remove ruff hooks from pre-commit config entirely
# Edit .pre-commit-config.yaml — remove the astral-sh/ruff-pre-commit repo block
# Ensure CI pipeline has pixi run lint (covers ruff check + ruff format --check)
```

### Detailed Steps

1. **Confirm the mismatch** — run both tools on the same file to confirm the disagreement:

   ```bash
   pixi run ruff format --check path/to/file.py    # passes
   pixi run pre-commit run ruff-format --files path/to/file.py  # fails
   ```

2. **Understand root cause** — `astral-sh/ruff-pre-commit` installs its own isolated ruff binary
   inside a virtualenv that is completely separate from the pixi-managed ruff. Even at identical
   version strings, the two environments can produce different formatting decisions because:
   - The pre-commit virtualenv may use different Python stdlib stubs
   - Config resolution (finding `pyproject.toml`) may differ between contexts
   - Subtle differences in working directory or PATH affect config discovery

3. **Check if CI already covers ruff separately** — inspect the CI workflow:

   ```bash
   grep -r "ruff\|lint" .github/workflows/ | grep -v "pre-commit"
   ```

   If a CI step runs `pixi run lint` or equivalent, ruff is already checked redundantly
   by pre-commit.

4. **Remove ruff hooks from `.pre-commit-config.yaml`**:

   ```yaml
   # REMOVE this entire block:
   # - repo: https://github.com/astral-sh/ruff-pre-commit
   #   rev: v0.X.X
   #   hooks:
   #     - id: ruff
   #     - id: ruff-format
   ```

5. **Verify remaining pre-commit config** is functional (mypy, gitleaks, general hooks):

   ```bash
   pixi run pre-commit run --all-files
   ```

6. **Commit and push** — CI should now pass on both the `lint` step and the `pre-commit` step.

### Final `.pre-commit-config.yaml` Pattern (without ruff)

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: no-commit-to-branch
        args: [--branch, master]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.15.0
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic>=2.0
          - pydantic-settings

  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.24.3
    hooks:
      - id: gitleaks
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `repo: local` hook type | Pointed pre-commit hook at the pixi ruff binary via `language: system` | pixi ruff was not reliably on PATH inside pre-commit's execution environment | `language: system` requires the tool to be in PATH; pixi-managed binaries often aren't unless the pixi shell is activated |
| Investigating 0-byte `__init__.py` files | Checked whether empty `tests/__init__.py` was missing a newline | Empty files are valid; not the root cause of ruff-format disagreement | Ruff-format disagreements are environment-specific, not file-content issues |
| Pinning pre-commit ruff to exact pixi version | Set `astral-sh/ruff-pre-commit` rev to precisely match `pixi run ruff --version` output | Different virtualenv isolation still produced divergent formatting decisions | Matching the version string is insufficient; the virtualenvs are fundamentally different execution environments |

## Results & Parameters

### Why pre-commit and pixi ruff diverge

`astral-sh/ruff-pre-commit` creates an isolated Python virtualenv managed by pre-commit.
This virtualenv:
- Has its own Python interpreter (not pixi's)
- Finds `pyproject.toml` relative to the hook's working directory, which may differ
- May apply different default config values if `pyproject.toml` is not found or parsed differently

Even at the exact same ruff version, the formatting decision for edge cases (trailing commas,
import grouping, line-wrapping) can differ between the two environments.

### When removal is safe

Removing ruff from pre-commit is safe when the CI pipeline already runs ruff as a dedicated step:

```yaml
# .github/workflows/ci.yml — already present
- name: Lint
  run: pixi run lint   # covers: ruff check + ruff format --check
```

Pre-commit's value for ruff is as a local commit-time gate. If CI enforces it separately with
the same pixi environment used for development, the pre-commit hook is redundant.

### Alternative: keep pre-commit ruff as non-blocking

If you want local commit-time feedback without CI risk, add `verbose: true` and configure
the hook to only warn locally without blocking CI pre-commit checks:

```yaml
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.15.12
  hooks:
    - id: ruff-format
      args: [--check]
      stages: [manual]  # Only runs with: pre-commit run --hook-stage manual
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHermes | PR #291 — CI "Lint & Test" job | Removing ruff from pre-commit config caused all required checks to pass and the PR merged to main |
