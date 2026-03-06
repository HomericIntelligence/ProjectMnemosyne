---
name: mojo-type-alias-cleanup
description: "Fix Mojo compilation errors caused by non-existent type aliases introduced when removing deprecated type aliases. Use when: CI fails with unknown type errors after removing deprecated aliases."
category: ci-cd
date: 2026-03-06
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Name** | mojo-type-alias-cleanup |
| **Category** | ci-cd |
| **Trigger** | CI Mojo compilation failure with unknown type names after deprecated alias removal |
| **Effort** | Low — find-and-replace with correct canonical types |

## When to Use

- CI fails with "unknown type" errors in Mojo after a PR removes deprecated `comptime` type aliases
- The PR replaced deprecated aliases with new names that were never defined
- Need to trace what each removed alias originally aliased to, and use those canonical types directly

## Verified Workflow

1. **Read the CI failure message** to identify which unknown type names appear and at which lines.

2. **Check what the removed aliases originally aliased to** by consulting the issue/PR description or git history:
   ```bash
   git log --all --oneline --diff-filter=D -S "alias DeprecatedName" -- path/to/file.mojo
   git show <commit>:path/to/file.mojo | grep "alias DeprecatedName"
   ```

3. **Grep for all occurrences** of the bad type names in the affected file:
   ```bash
   # Using Grep tool (preferred)
   Grep pattern="BadType1|BadType2" path="shared/core/conv.mojo" output_mode="content" context=1
   ```

4. **Confirm canonical types are imported** at the top of the file:
   ```bash
   Grep pattern="^from .* import" path="shared/core/conv.mojo" output_mode="content" head_limit=25
   ```

5. **Replace all occurrences** using `replace_all=true` in the Edit tool — one call per bad type name:
   ```
   Edit file, old_string="BadTypeName", new_string="CanonicalTypeName", replace_all=true
   ```

6. **Verify zero occurrences remain**:
   ```
   Grep pattern="BadType1|BadType2" — expect 0 matches
   ```

7. **Run mojo format** (if available locally):
   ```bash
   pixi run mojo format shared/core/conv.mojo
   ```
   If mojo cannot run locally (GLIBC mismatch), skip with `SKIP=mojo-format` and let CI handle it.

8. **Commit** with `SKIP=mojo-format` if needed:
   ```bash
   SKIP=mojo-format git commit -m "fix: replace non-existent type aliases with canonical types"
   ```

## Alias Mapping Reference (ProjectOdyssey conv.mojo)

When removing deprecated `DepthwiseConv2d*` and `DepthwiseSeparableConv2d*` aliases:

| Deprecated Alias | Canonical Type | Reason |
|-----------------|---------------|--------|
| `DepthwiseConv2dBackwardResult` | `GradientTriple` | Returns input, kernel, bias (3 values) |
| `DepthwiseConv2dNoBiasBackwardResult` | `GradientPair` | Returns input, kernel (2 values) |
| `DepthwiseSeparableConv2dBackwardResult` | `GradientQuad` | Returns input, depthwise kernel, pointwise kernel, bias (4 values) |
| `DepthwiseSeparableConv2dNoBiasBackwardResult` | `GradientTriple` | Returns input, depthwise kernel, pointwise kernel (3 values) |

**Key insight**: Count the number of values returned by the function to determine the correct
canonical type (`GradientPair`=2, `GradientTriple`=3, `GradientQuad`=4).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Used new descriptive names | PR replaced `DepthwiseConv2dBackwardResult` with `DepthwiseGradientTriple` | `DepthwiseGradientTriple` was never defined anywhere | When removing aliases, replace with the original aliased-to type, not a new invented name |
| Running `pixi run mojo format` locally | Tried to format before committing | GLIBC version mismatch on host (requires 2.32+ but host has older version) | Use `SKIP=mojo-format` for local commits; CI Docker environment has correct GLIBC |

## Results & Parameters

```bash
# Pattern for replacing multiple bad type names atomically
# Run one Edit call per type name with replace_all=true

# Verify before
grep -c "BadTypeName" shared/core/conv.mojo  # Should be > 0

# Replace (use Edit tool with replace_all=true)

# Verify after
grep -c "BadTypeName" shared/core/conv.mojo  # Should be 0

# Commit skipping mojo-format if mojo unavailable locally
SKIP=mojo-format git commit -m "fix: replace non-existent type aliases with canonical types

Closes #<issue>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```
