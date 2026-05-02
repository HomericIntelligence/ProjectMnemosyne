---
name: mojo-docstring-format-precommit
description: 'Enrich sparse Mojo test function docstrings to accurately describe what
  the test validates, pre-formatted to pass mojo format without producing a diff.
  Use when: (1) a one-liner docstring needs detail after feature support is added,
  (2) a split file got a minimal docstring, (3) stale placeholder language needs replacing
  in a test fn.'
category: documentation
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Objective** | Replace sparse or stale docstrings in Mojo test functions with accurate multi-line descriptions |
| **Trigger** | Issue flags a test fn docstring as inaccurate or placeholder; test is already active and passing |
| **Outcome** | Docstring updated, pre-commit passes, PR merged |
| **Time** | ~5 minutes |

## When to Use

- A Mojo test function docstring is a one-liner that doesn't describe what the test actually validates
- A file was split (e.g. `test_special_values.mojo` → `_part1/_part2/_part3`) and the new file got a minimal docstring
- The docstring says a feature is "not supported", "skipped", or "future" but the test is now active
- Closing a follow-up issue that flags stale docstring language after a feature lands

## Verified Workflow

### Quick Reference

| Step | Action |
|------|--------|
| 1 | Read issue + comments to get exact target file/function/line |
| 2 | Glob for the file (the original path may have changed due to splitting) |
| 3 | Grep for function name to confirm current docstring |
| 4 | Edit: replace one-liner with multi-line trailing-newline docstring |
| 5 | Verify line lengths ≤ 80-90 chars (4-space indent + `"""`) |
| 6 | Commit, push, create PR |

### Detailed Steps

1. **Read the issue plan** (`gh issue view <N> --comments`) to learn:
   - Original file path and line numbers (may be stale due to splits)
   - What the updated docstring should say

2. **Locate the actual file** — original path may have changed. Use Glob:

   ```bash
   find . -name "test_special_values*.mojo"
   # e.g. discovers test_special_values_part2.mojo
   ```

3. **Grep for the function** to see the current docstring:

   ```bash
   grep -n "test_dtypes_bfloat16" tests/shared/testing/test_special_values_part2.mojo
   ```

4. **Read the target lines** to confirm the exact text before editing (required by Edit tool).

5. **Apply the edit** — upgrade the one-liner to a multi-line docstring:

   ```mojo
   # BEFORE (sparse one-liner)
   fn test_dtypes_bfloat16() raises:
       """Test special values work with bfloat16."""

   # AFTER (descriptive multi-line, trailing-newline pattern)
   fn test_dtypes_bfloat16() raises:
       """Test special values work with bfloat16.

       Verifies DType.bfloat16 is fully supported in Mojo's DType enum
       and integrates correctly with the ExTensor special values API.

       Tests:
       - Tensor creation with DType.bfloat16 dtype
       - dtype assertion confirms bfloat16 is preserved
       - Special value invariants hold for value 1.0 (FP-representable)
       """
   ```

   **Line-length rule**: Each line in the docstring body (4-space indent + `"""` + text)
   must stay ≤ ~90 chars to avoid `mojo format` reflow producing a diff.

6. **Documentation-only change** — do not modify function body, signature, or imports.

7. **Commit** with `docs(tests):` prefix and `Closes #<N>` in the body:

   ```bash
   git add tests/shared/testing/test_special_values_part2.mojo
   git commit -m "docs(tests): update test_dtypes_bfloat16 docstring to reflect bfloat16 full support

   Closes #3904"
   ```

8. **Create PR** with `--label documentation`.

## Mojo Multi-Line Docstring Pattern

The trailing-newline pattern is the correct Mojo style for multi-line docstrings:

```mojo
fn my_fn() raises:
    """One-line summary.

    Extended description paragraph.

    Tests:
    - item one
    - item two
    """
    # function body...
```

Key rules:

- Closing `"""` on its own line, indented to match opening
- Blank line between summary and extended body
- Lists use `-` prefix (not `*`)
- Keep all lines ≤ 90 chars including indent

## Results & Parameters

### Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3904, PR #4824 | [notes.md](../references/notes.md) |

### Commit Message Template

```text
docs(tests): update <function_name> docstring to reflect <feature> full support

<Extended explanation if needed.>

Closes #<issue-number>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Searching original file path | Globbed for `test_special_values.mojo` | File was split into `_part1/_part2/_part3` in a prior commit | Always glob with `*test_special_values*.mojo` when file might have been split |
| Using Edit without Read | Called Edit tool immediately | Edit tool requires a prior Read of the file | Always Read first, even for a single-line change |
| Assuming file was unchanged | Relied on line numbers from issue body | Issue said "lines 241-264" but split moved function to line 124 of `_part2` | Treat issue line numbers as hints only; Grep to confirm actual location |
