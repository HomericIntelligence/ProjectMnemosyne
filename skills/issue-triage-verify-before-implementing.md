---
name: issue-triage-verify-before-implementing
description: "Verify implementation status before coding. Use when: (1) issue references multiple sub-issues or prior work, (2) issue says 'implement or document status', (3) codebase has evolved since issue was filed."
category: debugging
date: 2026-03-25
version: "1.0.0"
user-invocable: false
tags: [issue-triage, verification, stale-todos, codebase-analysis]
---

# Verify Implementation Status Before Coding

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-25 |
| **Objective** | Implement ExTensor operations (matrix, shape, elementwise, statistical, slicing) per issue #3013 |
| **Outcome** | All operations were already implemented. Real work was updating 5 files with stale TODO comments pointing to #3013 |

## When to Use

- Issue consolidates multiple previously-closed sub-issues (#2717-#2721 in this case)
- Issue acceptance criteria says "implement **or document status**"
- Issue references specific file:line locations that may have changed since filing
- Issue has a detailed implementation plan in comments that may be outdated
- Codebase has had significant development since the issue was created

## Verified Workflow

### Quick Reference

```bash
# 1. Check if referenced files/functions exist
grep -r "fn split\|fn tile\|fn repeat\|fn permute" shared/core/shape.mojo

# 2. Check if functions are exported
grep "split\|tile\|repeat\|permute" shared/core/__init__.mojo

# 3. Run existing tests FIRST before writing any code
NATIVE=1 just test-group "tests/shared/core" "test_shape.mojo"

# 4. Search for stale TODO references to the issue
grep -r "TODO.*#3013\|Blocked on #3013\|pending.*#3013" --include="*.mojo" .

# 5. Only then make changes (update stale comments, not implement from scratch)
```

### Detailed Steps

1. **Read the issue plan carefully** - Check if it says "already implemented" for any categories. The plan for #3013 explicitly said "most operations already exist" but the natural instinct is still to start coding.

2. **Verify referenced files exist** - The issue referenced `shared/core/extensor.mojo:23-28` but this file didn't exist. File paths in issues go stale as code evolves.

3. **Run existing tests before writing code** - `test_shape.mojo` already tested split, tile, repeat, permute, broadcast_to and all passed. This proved the operations were implemented.

4. **Search for stale references** - `grep -r "TODO.*#3013"` found 5 files with outdated TODO comments. This was the actual work needed.

5. **Update stale TODOs to point to correct tracking issues** - `TODO(#3013)` for `from_array()` should have been `TODO(#4127)`. CIFAR-10 loading references should point to #3076 (Python-Mojo interop blocker).

6. **Verify no remaining stale references** - After changes, re-run the grep to confirm zero `TODO.*#3013` matches remain.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Initial plan to implement split/tile/repeat/permute | Read issue plan suggesting these needed implementation | All functions already existed in shape.mojo with full test coverage | Always verify current state before coding; issues filed weeks/months ago may describe problems already solved |
| Looking for extensor.mojo docstring TODOs | Issue referenced `shared/core/extensor.mojo:23-28` | File didn't exist - the ExTensor struct was never created or was renamed to AnyTensor | File paths in issues go stale; always glob/grep to find current locations |
| Searching for #2717-#2721 TODO references | Expected old issue numbers in code comments | A previous commit (4394dd7e) had already cleaned these up | Check git log for recent related commits before starting work |

## Results & Parameters

**Files changed**: 5 (all comment/docstring updates, zero functional code changes)

**Pattern for updating stale TODOs**:
```
# Before: TODO pointing to consolidated issue
# TODO(#3013): implement when from_array() ships

# After: TODO pointing to specific tracking issue
# TODO(#4127): implement when from_array() ships
```

**Time saved**: ~6 hours of unnecessary implementation work avoided by verifying first

**Key grep commands for issue triage**:
```bash
# Find all references to an issue number
grep -r "#ISSUE_NUM" --include="*.mojo" .

# Find only actionable TODOs (not just mentions)
grep -r "TODO.*#ISSUE_NUM\|Blocked on #ISSUE_NUM\|pending.*#ISSUE_NUM" --include="*.mojo" .

# Verify cleanup is complete
grep -r "TODO.*#ISSUE_NUM" --include="*.mojo" .  # Should return empty
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3013 - ExTensor Operations | PR #5111 created, all tests passing |
