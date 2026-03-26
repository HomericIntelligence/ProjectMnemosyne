---
name: ci-mypy-matrix-entry
description: "Add mypy type checking as a dedicated CI matrix entry in GitHub Actions test.yml. Use when: (1) mypy is configured in pyproject.toml but not enforced in CI, (2) adding type-checking enforcement alongside unit/integration test matrix, (3) pixi run mypy task argument duplication issues."
category: ci-cd
date: 2026-03-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - ci-cd
  - mypy
  - github-actions
  - pixi
  - type-checking
---

# Add mypy as CI Matrix Entry

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Add mypy type checking as a dedicated matrix entry in `.github/workflows/test.yml` so type errors block merges |
| **Outcome** | Successful — mypy runs as its own CI job alongside unit and integration tests |
| **Verification** | verified-local |

## When to Use

- A project has `[tool.mypy]` configured in `pyproject.toml` with strict settings but mypy is not run in CI
- You want mypy as a separate CI matrix entry (not just a pre-commit hook) for fast, independent feedback
- The project uses pixi for dependency management and you want a `pixi run mypy` task
- Pre-commit already runs mypy but CI should also enforce it independently

## Verified Workflow

> **Note:** Verified locally — `pixi run mypy` passes on all 36 source files. CI validation pending on PR #104.

### Quick Reference

```bash
# 1. Run mypy locally first to triage errors
pixi run mypy hephaestus/

# 2. Add pixi task (pixi.toml [tasks] section)
# mypy = "mypy hephaestus/"

# 3. Add matrix entry to test.yml
# test-type: [unit, integration, mypy]

# 4. Add conditional step
# - name: Run mypy type checking
#   if: matrix.test-type == 'mypy'
#   run: pixi run mypy

# 5. Verify
pixi run mypy
```

### Detailed Steps

1. **Triage existing errors** — Run `pixi run mypy hephaestus/` (or target directory) locally before touching CI config. Fix all errors first.

2. **Add `mypy` task to `pixi.toml`** — Under `[tasks]`, add:
   ```toml
   mypy = "mypy hephaestus/"
   ```
   This bakes the target directory into the task so `pixi run mypy` is all that's needed.

3. **Add `mypy` to the test matrix** in `.github/workflows/test.yml`:
   ```yaml
   strategy:
     matrix:
       test-type: [unit, integration, mypy]
   ```

4. **Add the conditional step** — Place it alongside the other test-type conditional steps:
   ```yaml
   - name: Run mypy type checking
     if: matrix.test-type == 'mypy'
     run: pixi run mypy
   ```

5. **Use `pixi run mypy` NOT `pixi run mypy hephaestus/`** — When the pixi task already includes the target path, passing it again causes a "Duplicate module" error because mypy receives the path twice. Always invoke the task name alone.

6. **Verify locally** — `pixi run mypy` should exit 0 with "Success: no issues found in N source files".

### Key Insight: Pixi Task Argument Duplication

When a pixi task is defined as `mypy = "mypy hephaestus/"`, running `pixi run mypy hephaestus/` appends the argument to the task command, resulting in `mypy hephaestus/ hephaestus/`. This causes mypy to see the package twice:

```
hephaestus/__init__.py: error: Duplicate module named "hephaestus"
(also at "hephaestus/__init__.py")
```

**Fix:** Use `pixi run mypy` (no extra arguments) in CI and locally. The task definition already includes the target.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `pixi run mypy hephaestus/` in CI | Used `pixi run mypy hephaestus/` as the CI step command after defining `mypy = "mypy hephaestus/"` in pixi.toml tasks | "Duplicate module named hephaestus" — pixi appends CLI args to the task command, resulting in `mypy hephaestus/ hephaestus/` | When a pixi task already includes arguments, do not repeat them; use `pixi run mypy` alone |

## Results & Parameters

### pixi.toml task

```toml
[tasks]
mypy = "mypy hephaestus/"
```

### test.yml matrix entry

```yaml
strategy:
  matrix:
    test-type: [unit, integration, mypy]

# ...

- name: Run mypy type checking
  if: matrix.test-type == 'mypy'
  run: pixi run mypy
```

### pyproject.toml mypy config (reference)

```toml
[tool.mypy]
python_version = "3.10"
warn_unused_configs = true
ignore_missing_imports = true
show_error_codes = true
check_untyped_defs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
disallow_any_generics = true
warn_return_any = true
warn_redundant_casts = true
warn_unused_ignores = true
allow_redefinition = false
implicit_reexport = false
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #55, PR #104 | Added mypy CI matrix entry; 36 source files pass cleanly |
