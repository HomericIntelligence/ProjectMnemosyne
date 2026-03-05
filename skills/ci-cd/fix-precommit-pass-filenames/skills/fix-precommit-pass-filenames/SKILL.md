---
name: fix-precommit-pass-filenames
description: "Fix pre-commit hooks that use pass_filenames: false when they should use pass_filenames: true, removing hardcoded directory args so pre-commit passes only changed files. Use when: hooks always scan entire directories instead of only changed files, or linter entry commands have hardcoded directory paths."
category: ci-cd
date: 2026-03-05
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | fix-precommit-pass-filenames |
| **Category** | ci-cd |
| **Complexity** | S (small) |
| **Language** | YAML |
| **File** | `.pre-commit-config.yaml` |

## When to Use

- A pre-commit hook uses `pass_filenames: false` but also specifies a `files:` pattern — this combination means the hook always runs on the full directories regardless of what changed
- Ruff (or similar linter) hooks have hardcoded directory paths in `entry` (e.g., `ruff format scripts/ tests/`) instead of relying on pre-commit's file filtering
- Hooks are noticeably slow on commits touching a single file
- Issue/PR description says "use pass_filenames: true and remove hardcoded directories"

## Verified Workflow

1. Read `.pre-commit-config.yaml` to identify affected hooks
2. For each hook with `pass_filenames: false` and a `files:` pattern:
   - Change `pass_filenames: false` → `pass_filenames: true`
   - Remove hardcoded directory args from `entry` (keep only the command and fixed flags)
   - The `files:` pattern already restricts which files are passed — no other changes needed
3. Run `pixi run pre-commit run --all-files` to verify all hooks still pass
4. Commit and push; create PR with `Closes #<issue>`

### Example transformation

Before:

```yaml
- id: ruff-format-python
  entry: pixi run ruff format scripts/ examples/ tests/ tools/
  files: ^(scripts|examples|tests|tools)/.*\.py$
  pass_filenames: false
```

After:

```yaml
- id: ruff-format-python
  entry: pixi run ruff format
  files: ^(scripts|examples|tests|tools)/.*\.py$
  pass_filenames: true
```

Pre-commit will now call `pixi run ruff format <file1> <file2> ...` with only the changed
files that match the `files:` pattern.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running `just pre-commit-all` | Used `just` command runner | `just` not in PATH on this machine | Fall back to `pixi run pre-commit run --all-files` directly |
| Removing `files:` pattern too | Considered removing `files:` alongside adding `pass_filenames: true` | Not needed — `files:` is still required to restrict hook to Python files | Only remove the hardcoded dirs from `entry`; keep `files:` intact |

## Results & Parameters

### Verified config snippet (ruff hooks)

```yaml
- id: ruff-format-python
  name: Ruff Format Python
  entry: pixi run ruff format
  language: system
  files: ^(scripts|examples|tests|tools)/.*\.py$
  types: [python]
  pass_filenames: true

- id: ruff-check-python
  name: Ruff Check Python
  entry: pixi run ruff check --fix
  language: system
  files: ^(scripts|examples|tests|tools)/.*\.py$
  types: [python]
  pass_filenames: true
```

### Verification command

```bash
pixi run pre-commit run --all-files
# Expected: Ruff Format Python...Passed, Ruff Check Python...Passed
```

### Note on GLIBC errors

The `mojo-format` hook may produce GLIBC version errors on older Linux systems (Debian 10).
These are pre-existing environment limitations unrelated to `pass_filenames` changes and do
not cause the hook to fail CI (CI runs inside Docker with newer glibc).
