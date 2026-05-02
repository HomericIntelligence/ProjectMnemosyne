---
name: mojo-reexport-limitation-audit
description: 'Audit Mojo __init__.mojo submodules for re-export limitations and document
  findings in module docstrings. Use when: (1) a follow-up issue asks to check if
  the re-export limitation from one submodule also affects sibling submodules, (2)
  a cleanup sweep requires confirming which submodules have or lack re-export limitations,
  (3) a docstring audit reveals some submodules are undocumented about import path
  correctness.'
category: documentation
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# Skill: mojo-reexport-limitation-audit

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-03-07 |
| Objective | Audit `shared/training/` submodule `__init__.mojo` files for re-export limitations and add `Note:` sections documenting findings |
| Outcome | Success — 4 submodule docstrings updated confirming clean re-export; 0 new limitations found |
| Category | documentation |
| Related Skills | `mojo-module-docstring-limitation` (documenting a known limitation), `mojo-limitation-note-standardization` (standardizing NOTE format) |

## When to Use

Use this skill when:

- A GitHub issue is a follow-up to a re-export limitation fix (e.g., "check if the same limitation affects sibling submodules")
- A cleanup sweep (e.g., issue #3059 sweep) requires auditing all `__init__.mojo` files in a package
- Some submodules are documented about import limitations but sibling submodules are silent on the topic
- You need to confirm which submodules have limitations vs. which export cleanly

## Verified Workflow

### 1. Read the issue and prior context

```bash
gh issue view <number> --comments
```

Also read the parent issue (e.g., the original re-export fix) to understand what was already documented.

### 2. Locate all `__init__.mojo` files in the package

```
Glob pattern="<package>/**/__init__.mojo"
```

### 3. Grep for re-export limitation NOTEs

```
Grep pattern="# NOTE.*[Rr]e-export|# NOTE.*submodule|# NOTE.*[Ii]mport.*[Ll]imitation"
     glob="__init__.mojo"
     output_mode="content"
```

### 4. Read each `__init__.mojo`

Read all submodule init files to understand their current docstrings and what they export.

### 5. Categorize findings

Two outcomes per submodule:
- **Has limitation** → Add a `Note:` section documenting the broken/working import pattern
  (follow `mojo-module-docstring-limitation` skill for this case)
- **No limitation (clean re-export)** → Add a `Note:` section confirming clean export and
  cross-referencing the submodule that does have a limitation

### 6. Add `Note:` sections to clean submodules

For submodules with no re-export limitation, add this template to the module docstring:

```mojo
"""
[Existing docstring content]

Note:
    All symbols in this module are re-exported cleanly through the parent
    `<parent.package>` package. You may import directly from either location:

    ```mojo
    from <parent.package.submodule> import <Symbol>
    from <parent.package> import <Symbol>  # also works
    ```

    No Mojo re-export limitation applies here (unlike `<parent.package.limited_submodule>`).
"""
```

Key elements:
- Show both valid import forms
- Explicitly name the one submodule that *does* have a limitation (cross-reference)
- Use a concrete symbol example from that submodule

### 7. Run pre-commit hooks

```bash
pixi run pre-commit run --all-files
```

All hooks should pass for documentation-only changes.

### 8. Commit, push, create PR

```bash
git add <changed files>
git commit -m "docs(<scope>): document import limitations audit for <package> submodules

Closes #<number>"
git push -u origin <branch>
gh pr create --title "..." --body "Closes #<number>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Using `just pre-commit-all` | Ran `just` command runner | `just: command not found` in this environment | Use `pixi run pre-commit run --all-files` instead |
| Broad `# NOTE` grep on all files | Initial grep for any NOTE in `__init__.mojo` | Returned too many irrelevant NOTEs (method-level notes, inline comments) | Narrow to `# NOTE.*[Rr]e-export` or `# NOTE.*submodule` patterns |

## Results & Parameters

### Template for clean re-export Note

```mojo
Note:
    All symbols in this module are re-exported cleanly through the parent
    `<parent.package>` package. You may import directly from either location:

    ```mojo
    from <parent.package.submodule> import <ExampleSymbol>
    from <parent.package> import <ExampleSymbol>  # also works
    ```

    No Mojo re-export limitation applies here (unlike `<parent.package.limited_submodule>`).
```

### Grep patterns for audit

- Find re-export limitation NOTEs: `# NOTE.*[Rr]e-export|# NOTE.*submodule`
- Find any NOTE in init files: `# NOTE` with `glob="__init__.mojo"`
- Find import limitation patterns: `# NOTE.*directly.*import|# NOTE.*cannot.*import`

### Scope of ProjectOdyssey issue #3210

- `shared/training/__init__.mojo` — callbacks limitation already documented (#3091) ✅
- `shared/training/optimizers/__init__.mojo` — no limitation, confirmation note added ✅
- `shared/training/schedulers/__init__.mojo` — no limitation, confirmation note added ✅
- `shared/training/metrics/__init__.mojo` — no limitation, confirmation note added ✅
- `shared/training/loops/__init__.mojo` — no limitation, confirmation note added ✅

### Pre-commit behavior

- `mojo-format` passes (documentation changes don't introduce format violations)
- All other hooks (trailing-whitespace, end-of-file, yaml, markdown) pass for `.mojo` docstring edits
