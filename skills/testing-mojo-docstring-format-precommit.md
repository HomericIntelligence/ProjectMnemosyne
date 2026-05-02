---
name: mojo-docstring-format-precommit
description: 'Fix Mojo docstring formatting to pass mojo format pre-commit hook. Use
  when: single-line docstrings trigger mojo format CI failures.'
category: testing
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | `mojo format` reformats long single-line docstrings by splitting the closing `"""` to its own line |
| **Symptom** | Pre-commit CI fails with diff showing `"""..."""` changed to multiline form |
| **Root Cause** | `mojo format` enforces a line length limit; single-line docstrings exceeding it are split |
| **Fix** | Pre-emptively write the closing `"""` on its own line for any long docstring |

## When to Use

- Pre-commit CI fails with a `mojo format` diff that converts single-line docstrings to two-line form
- Writing new Mojo docstrings longer than ~80 characters
- Reviewing Mojo test files before committing to catch docstring length issues early

## Verified Workflow

1. **Identify the failures** by reading the CI log diff:
   ```
   -    """Long single-line docstring that exceeds limit."""
   +    """Long single-line docstring that exceeds limit.
   +    """
   ```

2. **Apply the fix** — move the closing `"""` to its own line for any affected docstring:
   ```mojo
   # Before (causes mojo format to reformat)
   fn my_func() raises:
       """This is a long docstring that exceeds the mojo format line length threshold."""

   # After (matches what mojo format produces)
   fn my_func() raises:
       """This is a long docstring that exceeds the mojo format line length threshold.
       """
   ```

3. **Use Edit tool** with exact old_string/new_string matching (one fix per Edit call):
   ```
   old_string: '    """Long description."""'
   new_string:  '    """Long description.\n    """'
   ```

4. **Commit and push** — CI re-runs and passes.

## Threshold

`mojo format` splits single-line docstrings when they exceed approximately **80–90 characters** including the indentation and triple-quote markers. In practice, any docstring over ~70 characters of content is at risk.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Write file directly without re-reading worktree file | Called `Write` tool on worktree file after reading main repo copy | Write tool requires reading the exact file path before writing; worktree files are separate from main repo files | Always read the worktree path (`/.worktrees/<branch>/`) not the main repo path before editing |
| Skip pre-commit CI check | Assumed all checks passed since main Comprehensive Tests all succeeded | `pre-commit` is a separate workflow job; it can fail independently | Always check all workflow jobs, not just the main test suite |

## Results & Parameters

**Exact diff from CI failure:**
```diff
-    """Create a DataLoader with n_batches * 4 samples, batch_size=4, feature_dim=10."""
+    """Create a DataLoader with n_batches * 4 samples, batch_size=4, feature_dim=10.
+    """
```

**Three docstrings fixed in one session** — all were helper/test function docstrings that described parameters in the single line.

**Pattern**: `fn <name>(<params>) raises -> <type>:` with a descriptive docstring tends to be the longest since the parameters are often restated.
