---
name: fix-mypy-ruff-script-ci
description: Fix mypy and ruff CI failures in Python scripts. Use when CI fails with
  F841 unused variables, F541 bare f-strings, or mypy list invariance errors.
category: ci-cd
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# Skill: Fix Mypy and Ruff Script CI Failures

## Overview

| Attribute | Value |
|-----------|-------|
| Name | fix-mypy-ruff-script-ci |
| Category | ci-cd |
| Description | Fix mypy and ruff CI failures in Python scripts caused by unused variables, missing type annotations, and bare f-strings |

## When to Use

- CI `mypy` job fails with "Incompatible return value type" on a list that contains `None` elements
- CI `mypy` job fails with "Need type annotation for ..." on local variables
- CI `ruff-check-python` fails with F841 (local variable assigned but never used)
- CI `ruff-check-python` fails with F541 (f-string without any placeholders)
- CI `ruff-format-python` fails with "files were modified by this hook"
- `validate-scripts` job fails citing the same ruff errors

## Verified Workflow

### 1. Get the exact errors from CI logs

```bash
gh run view --job <job-id> --log | grep -E "error:|F[0-9]+"
```

### 2. Fix mypy list invariance error

**Pattern**: `list[tuple[str, Path, None]]` is not compatible with `list[tuple[str, Path, Optional[str]]]`

**Root cause**: mypy infers the list type from first `append()` call. If the first append uses `None` (not `Optional[str]`), the list type is locked as `None`, not `Optional[str]`.

**Fix**: Add an explicit type annotation to the variable declaration:

```python
# Before (mypy error)
skills = []

# After (mypy passes)
skills: list[tuple[str, Path, Optional[str]]] = []
```

### 3. Fix mypy "Need type annotation" for Optional variables

**Pattern**: Variables initialized to `None` that are later assigned `str` values need `Optional[str]` annotations.

```python
# Before (mypy error)
workflow_section = None
failed_section = None

# After (mypy passes)
workflow_section: Optional[str] = None
failed_section: Optional[str] = None
```

### 4. Fix F841 unused variables

**Pattern**: Variables assigned but never read (often leftover from refactoring or dead code).

```python
# Before (F841: ordered_headers assigned but never used)
ordered_headers = ["## When to Use", "## Verified Workflow"]
pre_workflow = []
post_workflow_order = []

# After: simply remove the unused variables
```

### 5. Fix F541 f-string without placeholders

```python
# Before (F541)
print(f"Migration Summary:")

# After
print("Migration Summary:")
```

### 6. Run ruff format to fix style issues

```bash
pixi run ruff format scripts/<script>.py
```

### 7. Verify all checks pass locally

```bash
pixi run ruff check scripts/<script>.py
pixi run ruff format --check scripts/<script>.py
pixi run mypy --exclude 'generators/' scripts/
pixi run pre-commit run --files scripts/<script>.py
```

### 8. Commit and push

```bash
git add scripts/<script>.py
git commit -m "fix(scripts): fix mypy and ruff errors in <script>.py"
git push origin <branch>
```

If the remote branch has been force-updated (diverged), pull with rebase first:

```bash
git pull --rebase origin <branch>
git push origin <branch>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Direct push | `git push origin <branch>` after rebase | Remote had been force-pushed; local was behind | Always `git pull --rebase origin <branch>` before pushing when collaborating |
| Fixing only mypy errors | Added `Optional[str]` annotations but left unused variables | Ruff F841 still failed in validate-scripts job | Both mypy and ruff errors must be fixed together |

## Results & Parameters

**Common mypy errors in migration/porting scripts**:

| Error Code | Pattern | Fix |
|------------|---------|-----|
| `[return-value]` | `list[T1]` returned where `list[T1 | T2]` expected | Annotate the list: `skills: list[tuple[str, Path, Optional[str]]] = []` |
| `[annotation-needed]` | `None`-initialized variable later assigned different type | Add `Optional[T]` annotation: `var: Optional[str] = None` |

**Common ruff errors in scripts**:

| Code | Pattern | Fix |
|------|---------|-----|
| F841 | `x = [...]` assigned but never used | Remove the variable |
| F541 | `f"string without {placeholders}"` | Convert to plain string |
| E501 | Line too long | Let `ruff format` handle it automatically |

**Run order for CI parity**:

```bash
# Match CI checks exactly
pixi run ruff check scripts/
pixi run ruff format --check scripts/
pixi run mypy --exclude 'generators/' scripts/
```
