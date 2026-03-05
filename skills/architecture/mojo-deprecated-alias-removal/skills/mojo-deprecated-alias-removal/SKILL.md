---
name: mojo-deprecated-alias-removal
description: "Remove deprecated Mojo comptime type aliases and replace usages with canonical types. Use when: cleaning up DEPRECATED comptime aliases from Mojo modules, replacing old result type aliases with canonical gradient types, and deleting backward-compat test files."
category: architecture
date: 2026-03-05
user-invocable: false
---

# Mojo Deprecated Alias Removal

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-05 |
| **Objective** | Remove 6 deprecated `comptime` type aliases from `shared/core/conv.mojo` and update all usages |
| **Outcome** | Successfully removed all 6 aliases, deleted backward-compat test file, pre-commit hooks pass |
| **Issue** | #3064 - Remove deprecated Conv backward result type aliases |
| **PR** | #3264 |

## When to Use

Use this workflow when:

- Mojo modules contain `comptime Foo = Bar` aliases marked `# DEPRECATED`
- Backward compatibility aliases for result/gradient types need removal after type consolidation
- A test file exists solely to test deprecated aliases (`test_backward_compat_aliases.mojo`)
- The `__init__.mojo` re-exports deprecated aliases that should be pruned
- Cleanup phase: type consolidation ADR completed, canonical types established

**Trigger Conditions:**

- `grep -r "DEPRECATED" shared/ --include="*.mojo"` returns comptime alias lines
- Issue title contains "Remove deprecated ... type aliases"
- Issue references `GradientTriple`, `GradientPair`, `GradientQuad` as replacements

## Verified Workflow

### Phase 1: Discovery

```bash
# Find all usages across codebase (exclude worktrees!)
grep -r "OldAliasName" /path/to/repo --include="*.mojo" \
  --exclude-dir=".worktrees" --exclude-dir="build"

# Read the alias definitions to confirm mapping
# e.g., comptime Conv2dBackwardResult = GradientTriple
```

Key locations to check:

1. The definition file (e.g., `shared/core/conv.mojo`) — alias block AND function signatures/docstrings
2. `shared/core/__init__.mojo` — re-exports section
3. Layer files (e.g., `shared/core/layers/conv2d.mojo`) — imports
4. Test files — both the compat test file and regular test comments
5. Other worktrees (exclude from changes — they're separate branches)

### Phase 2: Implement Changes (Correct Order)

1. **Delete the backward-compat test file first** (prevents test failures mid-refactor):

   ```bash
   rm tests/shared/core/test_backward_compat_aliases.mojo
   ```

2. **Update layer imports** — remove deprecated alias from import statements:

   ```mojo
   # Before
   from shared.core.conv import conv2d, conv2d_backward, Conv2dBackwardResult

   # After
   from shared.core.conv import conv2d, conv2d_backward
   ```

3. **Update test comments** — replace deprecated alias names with canonical names in comments.

4. **Update `__init__.mojo`** — remove deprecated alias names from the `from shared.core.conv import (...)` block.

5. **Remove alias definitions from conv.mojo** — delete the entire DEPRECATED block:

   ```mojo
   # Delete this entire block:
   # Backward compatibility aliases using generic gradient containers
   # DEPRECATED: Use GradientTriple directly instead of Conv2dBackwardResult
   comptime Conv2dBackwardResult = GradientTriple
   # ... (all 6 aliases)
   ```

6. **Replace usages in function signatures and docstrings** using `replace_all`:

   ```python
   # Use Edit tool with replace_all=True for each alias:
   Edit(file, old="Conv2dBackwardResult", new="GradientTriple", replace_all=True)
   Edit(file, old="Conv2dNoBiasBackwardResult", new="GradientPair", replace_all=True)
   # etc.
   ```

### Phase 3: Verify

```bash
# Confirm no references remain (exclude worktrees and build dirs)
grep -r "OldAliasName" /repo --include="*.mojo" \
  --exclude-dir=".worktrees" --exclude-dir="build"

# Run pre-commit hooks
pixi run pre-commit run --all-files
```

### Phase 4: Commit in Worktree (Critical Pitfall Avoidance)

**IMPORTANT**: If changes were made in the main repo checkout but the PR branch is a worktree, copy the files explicitly:

```bash
# The worktree branch may already have some changes (e.g., __init__.mojo)
# from a prior partial implementation — always check git status in both places!

# Copy modified files from main checkout to worktree:
cp /path/to/main/shared/core/conv.mojo /path/to/worktree/shared/core/conv.mojo
cp /path/to/main/shared/core/layers/conv2d.mojo /path/to/worktree/shared/core/layers/conv2d.mojo
rm /path/to/worktree/tests/shared/core/test_backward_compat_aliases.mojo

# Then commit from the worktree:
cd /path/to/worktree
git add shared/core/conv.mojo shared/core/layers/conv2d.mojo
git rm tests/shared/core/test_backward_compat_aliases.mojo
git commit -m "cleanup(conv): remove deprecated Conv backward result type aliases"
git push origin <branch>
```

### Phase 5: PR

```bash
# Check if PR already exists before creating:
gh pr list --head <branch>

# If it exists, just enable auto-merge:
gh pr merge <pr-number> --auto --rebase

# If creating new:
gh pr create --title "..." --body "Closes #<issue>" --label "cleanup"
gh pr merge --auto --rebase
```

## Key Learnings

### Mojo-Specific: comptime Aliases

In Mojo, `comptime` aliases are compile-time type aliases:

```mojo
comptime Conv2dBackwardResult = GradientTriple
```

These are NOT the same as Python type aliases. When removing them:

- Replace with the RHS type (`GradientTriple`, `GradientPair`, `GradientQuad`)
- The alias deletion also removes the COMMENT block above it
- Function return types and docstrings both need updating

### Mojo-Specific: replace_all is Safe for Type Names

Using `Edit` with `replace_all=True` on a specific deprecated type name is safe because:

- Mojo type names are PascalCase — no risk of substring collision
- One `replace_all` pass handles signatures, docstrings, and body all at once

### Worktree Branch May Already Be Partially Done

Before making changes in the main checkout, check if the worktree branch already has some changes applied from a prior session. This happened with `__init__.mojo` and `test_conv.mojo` — they showed no diff after copying because the worktree already had those changes.

Always run `git diff` in both the main checkout AND the worktree before editing.

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Aliases removed | 6 comptime aliases |
| Files modified | 4 (`conv.mojo`, `__init__.mojo`, `layers/conv2d.mojo`, `test_conv.mojo`) |
| Files deleted | 1 (`test_backward_compat_aliases.mojo`, 291 lines) |
| Replacement types | `GradientTriple`, `GradientPair`, `GradientQuad` |
| Pre-commit result | All hooks pass (mojo format skipped — GLIBC mismatch on host) |
| CI validation | Runs in Docker where GLIBC constraint doesn't apply |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `pixi run mojo build shared` | Build to verify compilation locally | GLIBC version mismatch — Mojo requires GLIBC 2.32+ but host has older version | Local Mojo compilation is not possible on this host; rely on CI |
| `replace_all` on `DepthwiseSeparableConv2dBackwardResult` | Expected to find 4 usages in conv.mojo | String not found — the prior `replace_all` for `Conv2dBackwardResult` had already been applied in worktree | Check worktree branch state before applying changes; some may already be done |
| Making changes in main checkout without checking worktree | Edited main Odyssey2 checkout directly | Changes don't automatically appear in worktree branch — required manual copy | Always work in the worktree for the PR branch, or explicitly copy changed files |
