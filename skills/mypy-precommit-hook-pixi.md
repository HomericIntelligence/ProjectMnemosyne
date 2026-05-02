---
name: mypy-precommit-hook-pixi
description: 'Add mypy type checking as a pre-commit hook in a pixi-managed project.
  Use when: (1) adding mypy enforcement to pre-commit, (2) scripts have X|Y union
  syntax errors with default mypy version, (3) types-PyYAML stubs missing in mirrors-mypy
  isolated env.'
category: ci-cd
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# Skill: Add mypy Pre-Commit Hook (pixi projects)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-05 |
| **Objective** | Add `mypy` pre-commit hook to enforce Python type checking on `scripts/*.py` |
| **Outcome** | All hooks passing; `pixi run pre-commit run --all-files` green |
| **Issue** | ProjectOdyssey #3159 |

## When to Use

Use this skill when:

- A pixi-managed project has Python scripts with type hints but no mypy enforcement in pre-commit
- You need to add `mirrors-mypy` as a pre-commit hook and want it to pass out-of-the-box
- Scripts use `X | Y` union syntax (Python 3.10+) that mypy rejects with default `--python-version`
- The `mirrors-mypy` hook fails with "Library stubs not installed for yaml" (missing `types-PyYAML`)
- A `missing = []` list variable causes `var-annotated` errors from mypy

**Trigger phrases:**

- "Add mypy to pre-commit"
- "mypy hook failing with import-untyped"
- "X | Y syntax for unions requires Python 3.10"
- "Library stubs not installed for yaml"

## Verified Workflow

### Step 1: Verify mypy is in pixi.toml

```bash
grep "mypy" pixi.toml
grep "types-PyYAML" pixi.toml
```

If missing, add to `[dependencies]`:

```toml
mypy = ">=1.8.0,<2"
types-PyYAML = ">=6.0"
```

### Step 2: Run mypy locally to find errors before hooking

```bash
pixi run mypy scripts/ --ignore-missing-imports --no-strict-optional --explicit-package-bases
```

**Common errors to fix first:**

- `X | Y syntax for unions requires Python 3.10` — add `--python-version 3.10` or use `Optional[X]`
- `Need type annotation for "missing"` — annotate as `missing: list[str] = []`
- Module found twice under different names — add `--explicit-package-bases`

Verify clean with:

```bash
pixi run mypy scripts/ --ignore-missing-imports --no-strict-optional --explicit-package-bases --python-version 3.10
# Expected: Success: no issues found in N source files
```

### Step 3: Add hook to .pre-commit-config.yaml

```yaml
# Python type checking
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.8.0
  hooks:
    - id: mypy
      files: ^scripts/.*\.py$
      args: [--ignore-missing-imports, --no-strict-optional, --explicit-package-bases, --python-version, "3.10"]
      additional_dependencies: [types-PyYAML]
```

**Key points:**
- `additional_dependencies: [types-PyYAML]` — mirrors-mypy runs in an isolated venv; stubs must be declared here
- `--explicit-package-bases` — prevents "Source file found twice under different module names" when `scripts/` has subdirectories
- `--python-version "3.10"` — enables `X | Y` union syntax used in modern Python; pixi provides Python 3.14 but mypy defaults to an older version
- `files: ^scripts/.*\.py$` — scope to the target directory only

### Step 4: Verify the hook passes

```bash
pixi run pre-commit run mypy --all-files
# Expected: mypy...Passed

pixi run pre-commit run --all-files
# Expected: all hooks Passed
```

## Results & Parameters

| Parameter | Value |
| ----------- | ------- |
| `rev` | `v1.8.0` |
| `--python-version` | `3.10` |
| `additional_dependencies` | `[types-PyYAML]` |
| `--ignore-missing-imports` | Required — third-party libs without stubs |
| `--no-strict-optional` | Required — avoids noise on existing codebase |
| `--explicit-package-bases` | Required — scripts/ has subdirectories with no `__init__.py` |
| Files checked | 78 source files |
| PR | HomericIntelligence/ProjectOdyssey#3364 |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Run mypy without `--explicit-package-bases` | `pixi run mypy scripts/` | "Source file found twice under different module names" for `scripts/generators/templates.py` | scripts/ has subdirectories without `__init__.py`; always use `--explicit-package-bases` |
| Run mypy without `--python-version 3.10` | Default mypy python version | 6 errors: "X \| Y syntax for unions requires Python 3.10" | mypy defaults to a version < 3.10 even when runtime Python is 3.14; must explicitly set `--python-version 3.10` |
| Add mirrors-mypy hook without `additional_dependencies` | Standard hook config from issue spec | "Library stubs not installed for yaml" in 4 files | `mirrors-mypy` creates an isolated venv; stubs installed in pixi env are NOT available — must declare via `additional_dependencies` |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | PR #3364, issue #3159 | [notes.md](../../references/notes.md) |
