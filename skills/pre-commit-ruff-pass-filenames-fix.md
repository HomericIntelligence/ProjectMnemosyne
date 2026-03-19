---
name: pre-commit-ruff-pass-filenames-fix
description: 'Fix pre-commit ruff hooks to use pass_filenames: true and remove hardcoded
  directory args. Use when: ruff hooks scan all files instead of only staged files,
  or entry field has hardcoded directory paths.'
category: ci-cd
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# Pre-Commit Ruff pass_filenames Fix

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-05 |
| Objective | Fix ruff pre-commit hooks that ignore file scope due to missing `pass_filenames: true` |
| Issue | PR #3347, Issue #3154 in ProjectOdyssey |
| Outcome | Verified complete — hooks already correctly configured |

## When to Use

- `ruff-format-python` or `ruff-check-python` hooks scan the whole project on every commit
- The `entry` field in `.pre-commit-config.yaml` contains hardcoded directory paths (e.g. `ruff check .` or `ruff check scripts/`)
- CI pre-commit check fails because ruff runs on unrelated files
- You need ruff to only lint/format the files actually staged for commit

## Root Cause

Pre-commit passes staged filenames to hooks only when `pass_filenames: true` is set. Without it
(default is `true` for most hooks, but `false` for some custom configs), ruff receives no filenames
and either scans the working directory or uses its own default discovery. Hardcoded directory args
in `entry` compound the problem by always scanning that directory regardless of what was staged.

## Verified Workflow

1. **Locate hooks** — open `.pre-commit-config.yaml` and find `ruff-format-python` and `ruff-check-python` hook blocks

2. **Verify `pass_filenames`** — both hooks must have:

   ```yaml
   pass_filenames: true
   ```

3. **Remove hardcoded dirs from `entry`** — the `entry` field must NOT contain directory arguments:

   ```yaml
   # WRONG - hardcoded dir bypasses staged-file scope
   entry: ruff check scripts/

   # CORRECT - no hardcoded path; pre-commit passes staged files
   entry: ruff check
   ```

4. **Full correct hook block example**:

   ```yaml
   - id: ruff-check-python
     name: ruff-check-python
     language: system
     entry: ruff check
     types: [python]
     pass_filenames: true

   - id: ruff-format-python
     name: ruff-format-python
     language: system
     entry: ruff format
     types: [python]
     pass_filenames: true
   ```

5. **Verify locally**:

   ```bash
   just pre-commit-all
   ```

6. **Distinguish PR failures from pre-existing flaky CI** — after confirming hook config is correct,
   check if CI test failures are pre-existing:

   ```bash
   # View CI run failures on the PR
   gh pr checks <pr-number>

   # Compare with main branch CI history
   gh run list --branch main --limit 10
   gh run view <run-id> --log-failed
   ```

   Mojo runtime crashes (`mojo: error: execution crashed`) are a known intermittent infrastructure
   issue in ProjectOdyssey and are NOT caused by pre-commit hook changes.

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Hook IDs | `ruff-format-python`, `ruff-check-python` |
| Config file | `.pre-commit-config.yaml` |
| Required field | `pass_filenames: true` |
| Entry format | `ruff check` / `ruff format` (no directory args) |
| Local verify command | `just pre-commit-all` |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assuming changes were needed | Loaded review plan expecting to make code edits | The PR was already correctly implemented before the session started | Always verify current state with `git status` and `grep` before making any changes |
| Treating all CI failures as PR-related | Initially considered fixing flaky test failures | Failures were `mojo: error: execution crashed` — a pre-existing infra issue confirmed on `main` branch | Check `main` branch CI history to distinguish pre-existing flaky failures from PR-introduced regressions |
