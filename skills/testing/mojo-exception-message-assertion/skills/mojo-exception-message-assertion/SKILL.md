---
name: mojo-exception-message-assertion
description: "Pattern for asserting exact error message text in Mojo exception tests using 'except e:'. Use when: (1) upgrading bare except: clauses to assert specific error message text, (2) adding message verification to out-of-bounds or error-path tests."
category: testing
date: 2026-03-07
user-invocable: false
---

# Mojo Exception Message Assertion Pattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Issue** | #3389 — Verify `__setitem__` error message text in out-of-bounds test |
| **Objective** | Replace bare `except:` with `except e:` and assert `String(e) == "Index out of bounds"` |
| **Outcome** | ✅ Success — minimal test-only change, PR #4070 created with auto-merge enabled |

## When to Use

Use this skill when:

- A Mojo test uses a bare `except:` clause and needs to verify the specific error message text
- You are writing a follow-up to a test that only checks an error was raised (not what it says)
- An issue asks to match the `except e:` pattern used in analogous tests (e.g. `test_bool_requires_single_element`)
- You need to catch accidental changes to error message strings

## Verified Workflow

### 1. Identify the bare `except:` test to upgrade

Find tests using the manual-flag pattern:

```mojo
var raised = False
try:
    t[5] = 1.0
except:
    raised = True

if not raised:
    raise Error("...")
```

### 2. Find the existing import for assertions

Check the file's imports — prefer using already-imported helpers:

```bash
grep -n "assert_equal\|import testing" <test-file>.mojo
```

In ProjectOdyssey, `assert_equal` is re-exported from `shared.testing.assertions` via `tests/shared/conftest.mojo` and is already imported in most test files.

### 3. Apply the upgrade pattern

Replace the bare `except:` pattern with `except e:` + exact message assertion:

**Before:**

```mojo
var raised = False
try:
    t[5] = 1.0
except:
    raised = True

if not raised:
    raise Error("__setitem__ should raise error for out-of-bounds index")
```

**After:**

```mojo
var error_raised = False
try:
    t[5] = 1.0
except e:
    error_raised = True
    assert_equal(String(e), "Index out of bounds")

if not error_raised:
    raise Error("__setitem__ should raise error for out-of-bounds index")
```

Key changes:

- `raised` → `error_raised` (clearer name matching project convention)
- `except:` → `except e:` (binds the exception to variable `e`)
- Add `assert_equal(String(e), "<exact message>")` inside the except block
- The final `if not error_raised` guard stays — it still ensures the error was raised

### 4. Verify the exact error message string

The message must match the implementation exactly. Find it with:

```bash
grep -n "Index out of bounds\|raise Error" <package>/extensor.mojo
```

Use the literal string from the implementation (case-sensitive, exact match).

### 5. Commit and create PR

```bash
git add <test-file>.mojo
git commit -m "test(<scope>): verify error message in <test-name>

Closes #<issue>"
git push -u origin <branch>
gh pr create --title "test(<scope>): verify error message in <test-name>" \
  --body "Closes #<issue>" --label "testing"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Used `testing.assert_equal` directly | Called `testing.assert_equal(String(e), "...")` without importing `testing` | `testing` module not imported in the test file | Check existing imports first; use the project's `assert_equal` helper from conftest instead |
| Run mojo test locally | `pixi run mojo test tests/shared/core/test_utility.mojo` | GLIBC_2.32/2.33/2.34 not found on host | Mojo tests must run in Docker/CI on this dev machine; pre-commit hooks are the local gate |

## Results & Parameters

### Pattern Summary

| Component | Before | After |
|-----------|--------|-------|
| Exception binding | `except:` (bare) | `except e:` (named) |
| Variable name | `raised` | `error_raised` |
| Message assertion | None | `assert_equal(String(e), "exact message")` |
| Error-not-raised guard | `if not raised: raise Error(...)` | `if not error_raised: raise Error(...)` |

### Key Parameters

- Assert helper: `assert_equal` (already imported via conftest, not `testing.assert_equal`)
- Error message: exact string from implementation, e.g. `"Index out of bounds"`
- Final guard: keep the `if not error_raised` block — it ensures the error path was taken

### Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3389, PR #4070, follow-up from #3165 | [notes.md](../references/notes.md) |
