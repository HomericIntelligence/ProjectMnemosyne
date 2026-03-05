---
name: already-implemented-feature-detection
description: "Verify whether GitHub issue requirements are already fully implemented before starting work. Use when: implementing a GitHub issue on a branch that may have prior commits, or when a PR already exists for the issue."
category: tooling
date: 2026-03-05
user-invocable: false
---

## Overview

| Attribute | Value |
|-----------|-------|
| **Trigger** | Implementing a GitHub issue on a branch with existing commits |
| **Goal** | Avoid duplicating work that is already done; confirm all requirements are met |
| **Outcome** | Verification that implementation is complete OR identification of gaps |
| **Time Saved** | Prevents re-implementing already-working code |

## When to Use

- The worktree branch already has commits with "feat" or "implement" in the message
- `git log` shows recent commits that reference the issue number
- A PR already exists and is OPEN for the issue
- The issue title matches methods/functions already visible in the codebase

## Verified Workflow

1. **Check git log first** - look for commits referencing the issue

   ```bash
   git log --oneline -10
   ```

2. **Search for the methods/functions by name** in the relevant files

   ```bash
   grep -n "fn method_name\|fn clone\|fn item\|fn diff" path/to/file.mojo
   ```

3. **Read the test file** to understand what the tests expect

   ```bash
   # Read test file that the issue references
   cat tests/shared/core/test_utility.mojo
   ```

4. **Verify exports** match what the tests import

   ```bash
   grep -n "clone\|item\|diff" shared/core/__init__.mojo
   ```

5. **Check for existing PR**

   ```bash
   gh pr list --head <branch-name>
   ```

6. **If all implemented**: confirm PR has auto-merge enabled, report status to user

   ```bash
   gh pr view <pr-number>
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running mojo tests locally | `pixi run mojo test tests/shared/core/test_utility.mojo` | GLIBC version too old (2.31 < 2.32 required) | Always check if CI environment differs; local execution may not be possible |
| Assuming implementation was missing | Started planning to implement utility methods from scratch | Prior commit `20ddaee6` had already implemented all methods | Check `git log` BEFORE reading issue description |

## Results & Parameters

### Key Detection Signals

```bash
# Signal 1: Branch has relevant commits
git log --oneline -5
# Look for: feat(scope): implement ... (#issue-number)

# Signal 2: Methods already in codebase
grep -n "fn clone\|fn item\|fn diff\|fn tolist\|fn __len__" shared/core/extensor.mojo
# If returns results -> methods exist

# Signal 3: PR already created and open
gh pr list --head $(git branch --show-current)
# If returns rows -> PR exists

# Signal 4: PR has auto-merge enabled
gh pr view <number> | grep auto-merge
# If shows "enabled" -> implementation complete and waiting for CI
```

### Complete Verification Command Sequence

```bash
# 1. Check recent commits
git log --oneline -5

# 2. Grep for expected method names
grep -n "fn <method1>\|fn <method2>" path/to/implementation.mojo

# 3. Check exports
grep -n "<method1>\|<method2>" path/to/__init__.mojo

# 4. Check PR status
gh pr list --head $(git branch --show-current)

# 5. View PR details if it exists
gh pr view <number>
```

### Session Context

- **Issue**: #2722 - ExTensor utility methods (copy, clone, item, tolist, __setitem__, __len__, __hash__, diff, contiguous)
- **Branch**: `2722-auto-impl`
- **Prior commit**: `20ddaee6 feat(extensor): implement utility methods for ExTensor (#2722)`
- **PR**: #3161 - OPEN with auto-merge enabled
- **All methods verified present**: `__setitem__`, `__int__`, `__float__`, `__str__`, `__repr__`, `__hash__`, `contiguous`, `clone`, `item`, `tolist`, `diff`, `__len__`
- **Exports verified**: `clone`, `item`, `diff` all exported from `shared/core/__init__.mojo`
