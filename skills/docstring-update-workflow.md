---
name: docstring-update-workflow
description: 'Workflow for updating stale module-level docstring examples after API
  signature changes. Use when: a function signature changed and the module docstring
  still shows the old call, or a docstring example omits required arguments.'
category: documentation
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Goal** | Update a stale module-level docstring example to match the current function signature |
| **Trigger** | A function's signature changed (new required argument added), but the module docstring example still shows the old call |
| **Outcome** | Docstring example compiles and matches actual API; pre-commit hooks pass |
| **Risk** | Very low — docstring-only change, no functional code altered |

## When to Use

- A follow-up issue is opened after a function signature change (e.g., "update example after #NNNN")
- The module-level docstring shows a call that omits a now-required argument (e.g., missing `step_fn`)
- CI or a reviewer flags a misleading/broken example in documentation
- You need to demonstrate a non-trivial call that requires helper functions (e.g., `create_simple_dataloader`)

## Verified Workflow

### Quick Reference

```bash
# 1. Find the file
glob "**/module_name.mojo"

# 2. Read the current signature
grep "fn function_name" path/to/file.mojo -C 5

# 3. Find any helper constructors referenced
grep "fn create_" path/to/related_file.mojo -C 5

# 4. Edit the docstring to show a working call
edit path/to/file.mojo

# 5. Validate with pre-commit
pixi run pre-commit run --files path/to/file.mojo

# 6. Commit, push, and open PR
git add path/to/file.mojo
git commit -m "docs(module): update docstring example for function_name\n\nCloses #NNNN"
git push -u origin <branch>
gh pr create --title "..." --body "Closes #NNNN"
```

### Detailed Steps

1. **Read the issue** to understand which function's example is stale and what the new signature looks like.

2. **Locate the file** using `Glob` with a pattern like `**/module_name.mojo`.

3. **Read the current signature** with `Grep` targeting `fn function_name` with 5 lines of context.
   - Note every required parameter (no default value) — the example must pass all of them.

4. **Find helper constructors** if the example needs non-trivial inputs.
   - E.g., if the function takes a `DataLoader`, search for `fn create_simple_dataloader` in the same package.

5. **Edit the module docstring** (lines 1–N of the file):
   - Show all required imports at the top of the example block.
   - Include a minimal `fn step(...)` or equivalent stub if the function takes a callback.
   - Call any constructor helpers to build the required arguments.
   - Call the target function with all required arguments.

6. **Run pre-commit** on just the changed file:

   ```bash
   pixi run pre-commit run --files shared/training/script_runner.mojo
   ```

   All hooks (mojo format, trailing-whitespace, end-of-file-fixer) must pass before committing.

7. **Commit using conventional commits**:

   ```text
   docs(scope): update module docstring example for function_name

   Replace stale example (which omitted required_arg) with a working
   call that passes all required arguments.

   Closes #NNNN
   ```

8. **Push and open PR** linked to the issue.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Copying old example verbatim | Kept `print_training_header` + `TrainingCallbacks` pattern | Did not demonstrate `run_epoch_with_batches` at all | Always grep the actual function signature before writing the example |
| Referencing non-existent imports | Used `from shared.training.script_runner import run_epoch_with_batches` without checking available exports | Function was in the same file, import would be circular/redundant | Read the file fully to know which symbols need cross-module imports vs same-file usage |
| Omitting the `step_fn` stub | Showed `run_epoch_with_batches(loader, callbacks)` without `step` | Signature requires `step_fn: fn(ExTensor, ExTensor) raises -> ExTensor` | Check every parameter with no default value |

## Results & Parameters

### Verified Example (Mojo docstring pattern)

```mojo
"""Module description.

Example:
    ```mojo
    from shared.training.script_runner import (
        TrainingCallbacks,
        run_epoch_with_batches,
        print_training_header,
    )
    from shared.training.trainer_interface import (
        create_simple_dataloader,
    )
    from shared.core.extensor import ExTensor

    fn step(x: ExTensor, y: ExTensor) raises -> ExTensor:
        return x  # replace with real forward+loss

    var loader = create_simple_dataloader(
        data^, labels^, batch_size=32
    )
    var callbacks = TrainingCallbacks(verbose=True)
    var loss = run_epoch_with_batches(
        loader, callbacks, step
    )
    ```
"""
```

### Pre-commit Command

```bash
pixi run pre-commit run --files <path/to/file.mojo>
```

### PR Body Template

```markdown
## Summary

- Replace stale module-level docstring example in `path/to/module.mojo`
- New example shows `function_name` called with all required arguments
- No functional code changes — docstring only

## Verification

- `pixi run pre-commit run --files path/to/module.mojo` passes all hooks

Closes #NNNN
```
