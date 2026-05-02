---
name: mojo-module-docstring-limitation
description: 'Document Mojo re-export limitations in module docstrings when submodule
  symbols cannot be imported via the parent package. Use when: (1) a NOTE comment
  exists warning about an import limitation, (2) a GitHub issue asks to document a
  Mojo import workaround, (3) a module docstring is missing guidance for users who
  cannot import types from the parent package.'
category: documentation
date: 2026-03-04
version: 1.0.0
user-invocable: false
---
# Skill: mojo-module-docstring-limitation

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-03-04 |
| Objective | Document Mojo import limitation in `shared/training/__init__.mojo` module docstring |
| Outcome | Success — `Note:` section added with broken/working examples, PR #3206 created |
| Category | documentation |

## When to Use

Use this skill when:

- A module has an inline `# NOTE:` comment warning users about a Mojo import limitation
- A GitHub issue asks to "document a limitation" or "update user-facing documentation"
- A Mojo `__init__.mojo` re-exports symbols from submodules but users cannot import them
  from the parent package (a known Mojo re-export limitation)
- The module docstring is missing a `Note:` section explaining workarounds

## Verified Workflow

### 1. Read the issue and file context

```bash
gh issue view <number> --comments
```

Read the `__init__.mojo` file to find the existing `# NOTE:` comment and understand
the current docstring structure.

### 2. Locate the inline NOTE comment

Grep for the NOTE marker in the file:

```bash
grep -n "NOTE" shared/training/__init__.mojo
```

The comment text contains the exact import limitation to document.

### 3. Add Note: section to module docstring

Insert a `Note:` section at the end of the existing module docstring (just before
the closing `"""`). The note must include:

- **What fails**: The incorrect import pattern (from parent package)
- **What works**: The correct import pattern (from submodule directly)
- **Why**: A brief explanation of the Mojo re-export limitation
- **Code examples**: Both broken and working import patterns in ` ```mojo ` blocks

Example structure:

```mojo
"""
[Existing docstring text]

Note:
    **Callback Import Limitation**: Due to Mojo's module system, callback types cannot
    be imported directly from the `shared.training` parent module. They must be imported
    directly from the `shared.training.callbacks` submodule.

    This is a known limitation of Mojo's current re-export mechanism — symbols defined
    in a submodule and re-exported via `__init__.mojo` are not always resolvable at the
    parent package level when used as types in user code.

    Incorrect (will fail with a Mojo import error):

    ```mojo
    from shared.training import EarlyStopping
    ```

    Correct (import directly from the submodule):

    ```mojo
    from shared.training.callbacks import EarlyStopping
    ```
"""
```

### 4. Run pre-commit hooks

```bash
pixi run pre-commit run --all-files
```

Expected: mojo-format will fail due to GLIBC version mismatch in this environment
(pre-existing infrastructure issue). All other hooks should pass including
markdown lint, trailing whitespace, YAML check, and ruff.

### 5. Commit, push, create PR

```bash
git add shared/training/__init__.mojo
git commit -m "docs(training): document <limitation> in __init__.mojo

Closes #<issue>"
git push -u origin <branch>
gh pr create --title "..." --body "..."
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Running `just pre-commit-all` | Used `just` command runner | `just: command not found` in this environment | Use `pixi run pre-commit run --all-files` directly |
| mojo-format hook | Pre-commit mojo-format hook ran on `.mojo` files | GLIBC version mismatch (`GLIBC_2.32` not found) — infrastructure issue, not code | Skip mojo-format concern; it's a pre-existing environment limitation, not caused by the change |

## Results & Parameters

### Minimal docstring Note: section template

```mojo
Note:
    **<Type> Import Limitation**: Due to Mojo's module system, <type> types cannot
    be imported directly from the `<parent.module>` parent module. They must be imported
    directly from the `<parent.module.submodule>` submodule.

    This is a known limitation of Mojo's current re-export mechanism — symbols defined
    in a submodule and re-exported via `__init__.mojo` are not always resolvable at the
    parent package level when used as types in user code.

    Incorrect (will fail with a Mojo import error):

    ```mojo
    from <parent.module> import <TypeName>
    ```

    Correct (import directly from the submodule):

    ```mojo
    from <parent.module.submodule> import <TypeName>
    ```
```

### CI behavior

- `mojo-format` hook fails with GLIBC version mismatch in local environment
- All other pre-commit hooks pass for documentation-only changes
- CI on GitHub passes (uses Docker with correct GLIBC version)
