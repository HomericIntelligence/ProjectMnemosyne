---
name: pre-commit-hook-pass-filenames
description: 'Fix pre-commit hooks running on hardcoded directories instead of staged
  files by setting pass_filenames: true. Use when: ruff/linter hooks ignore staged
  files, hook entry has hardcoded paths, or PR review requests pass_filenames fix.'
category: ci-cd
date: 2026-03-06
version: 1.0.0
user-invocable: false
---
# Pre-commit Hook pass_filenames Fix

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-06 |
| **Issue** | #3154 - ruff pre-commit hooks running on hardcoded dirs instead of staged files |
| **Objective** | Fix ruff-format-python and ruff-check-python hooks to pass filenames correctly |
| **Outcome** | Success - Removed hardcoded dirs from `entry`, set `pass_filenames: true` |

## When to Use

Use this skill when:

- Pre-commit ruff (or other linter) hooks run on hardcoded directories instead of staged files
- Hook `entry` field contains hardcoded paths like `pixi run ruff format src/ scripts/`
- PR review feedback requests `pass_filenames: true` fix for formatter/linter hooks
- Hooks pass on all files but miss newly staged files not in hardcoded directories
- Review plan states the fix is already committed — verify before making changes

## Verified Workflow

### 1. Verify Current State Before Making Changes

Always read the review plan and check git log first:

```bash
# Check if fix is already committed
git log --oneline -5

# Check current hook configuration
cat .pre-commit-config.yaml
```

**Key Finding**: Review fix plans may describe a completed fix. Check `git log` before touching anything.

### 2. Identify the Problem Pattern

The broken pattern has hardcoded directories in `entry` and `pass_filenames: false` (or absent):

```yaml
# BROKEN - hardcoded dirs, filenames not passed
- id: ruff-format-python
  name: Ruff Format Python
  entry: pixi run ruff format src/ scripts/
  language: system
  types: [python]
  pass_filenames: false
```

### 3. Apply the Fix

Remove hardcoded directories from `entry`, set `pass_filenames: true`:

```yaml
# FIXED - no hardcoded dirs, filenames passed by pre-commit
- id: ruff-format-python
  name: Ruff Format Python
  entry: pixi run ruff format
  language: system
  types: [python]
  pass_filenames: true

- id: ruff-check-python
  name: Ruff Check Python
  entry: pixi run ruff check --fix
  language: system
  types: [python]
  pass_filenames: true
```

### 4. Verify Hooks Pass

```bash
pixi run pre-commit run --all-files
```

Expected output:

```
Ruff Format Python.......................................................Passed
Ruff Check Python........................................................Passed
```

### 5. Commit

```bash
git add .pre-commit-config.yaml
git commit -m "fix(pre-commit): use pass_filenames: true for ruff hooks

Closes #<issue-number>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running tests first | Ran `pixi run python -m pytest tests/ -v` | `ModuleNotFoundError: No module named 'scripts.dashboard'` — pre-existing unrelated failure | Pre-existing test failures are not blockers; verify they are unrelated before spending time on them |
| Assuming changes needed | Started planning edits to `.pre-commit-config.yaml` | Fix was already committed in `26669e4f` | Always check `git log` before implementing fixes from a review plan |

## Results & Parameters

### Working Hook Configuration

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: ruff-format-python
      name: Ruff Format Python
      entry: pixi run ruff format
      language: system
      types: [python]
      pass_filenames: true

    - id: ruff-check-python
      name: Ruff Check Python
      entry: pixi run ruff check --fix
      language: system
      types: [python]
      pass_filenames: true
```

### Verification Command

```bash
pixi run pre-commit run --all-files 2>&1 | grep -E "(Ruff|Passed|Failed)"
```

### Pre-existing CI Failures

If CI shows unrelated test failures (e.g., Mojo GLIBC errors, missing Python modules), confirm they
predate the PR by checking git history:

```bash
git log --oneline --all | head -20
# If failures exist before your branch diverged, they are not your responsibility
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #3347, Issue #3154 | [notes.md](../../references/notes.md) |
