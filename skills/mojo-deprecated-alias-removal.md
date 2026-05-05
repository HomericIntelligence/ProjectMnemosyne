---
name: mojo-deprecated-alias-removal
description: "Workflow for removing deprecated Mojo comptime type aliases and replacing usages with canonical types. Use when: removing DEPRECATED-marked comptime aliases from Mojo modules, cleaning up backward-compat test files, updating __init__.mojo exports and layer imports after alias consolidation."
category: architecture
date: 2026-03-05
version: 1.2.0
user-invocable: false
absorbed:
  - mojo-comptime-alias-removal
---
# Mojo Deprecated Alias Removal

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-05 |
| **Objective** | Remove deprecated `comptime` type aliases from Mojo modules and replace all usages with canonical types |
| **Outcome** | ✅ Successfully applied across Linear (2 aliases) and Conv (6 aliases) modules |
| **Issues** | #3065 (Linear), #3064 (Conv), #3267 (Conv follow-up) |
| **PRs** | #3262 (Linear), #3264 (Conv), #3833 (Conv follow-up) |

## When to Use This Skill

Use this workflow when you need to:

- **Remove `DEPRECATED`-marked `comptime` aliases** from Mojo source files
- **Replace alias usages** with canonical gradient/result types throughout a module
- **Clean up backward-compat test files** that test the now-removed aliases
- **Update `__init__.mojo` exports** to remove alias re-exports
- **Update layer imports** (e.g., `layers/conv2d.mojo`) that import deprecated aliases
- **Consolidate gradient return types** (e.g., `LinearBackwardResult` → `GradientTriple`)

**Trigger Conditions:**

- Mojo file contains `comptime AliasName = CanonicalType` with `# DEPRECATED` comment
- Issue requests removing backward-compat aliases as cleanup phase
- Module exports both the alias and the canonical type
- `grep -r "DEPRECATED" shared/ --include="*.mojo"` returns comptime alias lines
- Issue references `GradientTriple`, `GradientPair`, `GradientQuad` as replacements

## Verified Workflow

### Phase 1: Discovery

1. **Find all occurrences** of the deprecated alias names:

   ```bash
   # Find all usages across codebase (exclude worktrees and build dirs!)
   grep -rn "AliasName1\|AliasName2" --include="*.mojo" . \
     --exclude-dir=".worktrees" --exclude-dir="build"
   ```

2. **Catalog all affected files** — typically these categories:
   - The source module defining the alias (e.g., `shared/core/linear.mojo`, `shared/core/conv.mojo`)
   - The package `__init__.mojo` re-exporting the alias
   - Layer files that import the alias (e.g., `shared/core/layers/conv2d.mojo`)
   - The backward-compat test file (`test_backward_compat_aliases.mojo`)
   - Regular test files with comments referencing the alias

3. **Check worktree branch state** — if using worktrees, a prior session may have already applied some changes:

   ```bash
   # Always check both places before editing
   git diff   # in main checkout
   cd /path/to/worktree && git diff  # in worktree
   ```

### Phase 2: Update the Source Module

1. **Remove the alias definition block** including comments:

   ```mojo
   # BEFORE (remove all of this)
   # Backward compatibility aliases using generic gradient containers
   # DEPRECATED: Use GradientTriple directly instead of LinearBackwardResult
   comptime LinearBackwardResult = GradientTriple

   # DEPRECATED: Use GradientPair directly instead of LinearNoBiasBackwardResult
   comptime LinearNoBiasBackwardResult = GradientPair
   ```

2. **Replace usages in function signatures, return statements, and docstrings** — use `replace_all` since Mojo PascalCase type names are safe from substring collisions:

   ```python
   # Use Edit tool with replace_all=True for each alias:
   Edit(file, old="LinearBackwardResult", new="GradientTriple", replace_all=True)
   Edit(file, old="LinearNoBiasBackwardResult", new="GradientPair", replace_all=True)
   ```

### Phase 3: Update Function Signatures and Bodies in Source File

For each function that uses an alias type, update these three locations individually:

1. **Return type annotation**:

   ```mojo
   # BEFORE
   ) raises -> Conv2dBackwardResult:

   # AFTER
   ) raises -> GradientTriple:
   ```

2. **Docstring Returns section**:

   ```mojo
   # BEFORE
   Returns:
       Conv2dBackwardResult containing:

   # AFTER
   Returns:
       GradientTriple containing:
   ```

3. **Return statements** (alias constructors become direct type constructors):

   ```mojo
   # BEFORE
   return Conv2dBackwardResult(grad_input^, grad_kernel^, grad_bias^)

   # AFTER
   return GradientTriple(grad_input^, grad_kernel^, grad_bias^)
   ```

> **Note**: Using `Edit` with `replace_all=True` on PascalCase type names is safe and handles all three locations in one pass.

### Phase 4: Update `__init__.mojo` Exports

Remove the alias names from the module's import/export block:

```mojo
# BEFORE
from shared.core.linear import (
    linear,
    linear_backward,
    LinearBackwardResult,        # <-- Remove
    LinearNoBiasBackwardResult,  # <-- Remove
)

# AFTER
from shared.core.linear import (
    linear,
    linear_backward,
)
```

### Phase 5: Update Layer Files That Import Aliases

Remove deprecated aliases from layer file imports. Handle type annotation presence carefully:

```mojo
# Before
from shared.core.conv import conv2d, conv2d_backward, Conv2dBackwardResult

# After (if alias is only used in comments, just remove it)
from shared.core.conv import conv2d, conv2d_backward
```

If the alias is used as an actual type annotation (not just in comments), replace it with the
concrete type and add a direct import:

```mojo
from shared.core.gradient_types import GradientTriple
```

> **Key rule**: Only add a concrete-type import if the type is actually used in a type annotation. Comments do not require imports.

### Phase 6: Update Backward-Compat Test File

The `test_backward_compat_aliases.mojo` file may test multiple alias groups:

- **If removing ALL aliases**: Delete the entire test file
- **If removing SOME aliases (partial removal)**: Remove only the relevant imports, test functions, and `main()` calls, then update the test count:

  ```mojo
  # BEFORE
  from shared.core import (
      Conv2dBackwardResult,       # Remove
      Conv2dNoBiasBackwardResult, # Remove
      ...
  )

  fn main() raises:
      test_conv2d_backward_result_alias()         # Remove
      test_conv2d_no_bias_backward_result_alias() # Remove
      print("\n All 8 tests passed\n")  # Update count
  ```

Also update comments in regular test files that reference deprecated alias names:

```mojo
# BEFORE
# NOTE: Backward tests disabled due to ownership issues in Conv2dBackwardResult.

# AFTER
# NOTE: Backward tests disabled due to ownership issues in GradientTriple.
```

### Phase 7: Verification

1. **Confirm no alias references remain:**

   ```bash
   grep -rn "AliasName1\|AliasName2" --include="*.mojo" . || echo "✓ All removed"
   ```

2. **Run pre-commit hooks** (mojo format may fail locally due to GLIBC — that's OK):

   ```bash
   pixi run pre-commit run --all-files
   ```

3. **Build verification** must happen in CI/Docker due to GLIBC requirements:

   ```bash
   just docker-run pixi run mojo build shared
   ```

### Phase 8: Commit & PR

```bash
# If using worktrees, copy modified files to worktree first
# Check if PR already exists:
gh pr list --head <branch>

# Create PR and enable auto-merge:
gh pr create --title "cleanup(module): remove deprecated X type aliases" \
  --body "Closes #<issue>" --label "cleanup"
gh pr merge --auto --rebase
```

## Phase Detail Reference (Conv Module)

This section captures concrete details from applying the workflow to `shared/core/conv.mojo`
(Issue #3064, PR #3264) — 6 aliases removed across 5 files.

### Conv Module Aliases (6 total)

| Deprecated Alias | Replacement Type | Module |
| ------------------------------------------- | ---------------- | ---------------------- |
| `Conv2dBackwardResult` | `GradientTriple` | `shared/core/conv.mojo` |
| `Conv2dNoBiasBackwardResult` | `GradientPair` | `shared/core/conv.mojo` |
| `DepthwiseConv2dBackwardResult` | `GradientTriple` | `shared/core/conv.mojo` |
| `DepthwiseConv2dNoBiasBackwardResult` | `GradientPair` | `shared/core/conv.mojo` |
| `DepthwiseSeparableConv2dBackwardResult` | `GradientTriple` | `shared/core/conv.mojo` |
| `DepthwiseSeparableConv2dNoBiasBackwardResult` | `GradientPair` | `shared/core/conv.mojo` |

### Files Modified (Conv)

```text
shared/core/conv.mojo              - Remove alias definitions, update 6 functions
shared/core/__init__.mojo          - Remove 6 alias exports from import block
shared/core/layers/conv2d.mojo     - Remove alias import, update comment
tests/shared/core/test_backward_compat_aliases.mojo - Remove 4 test functions + imports (partial removal)
tests/shared/core/test_conv.mojo   - Update 2 comments
```

### Conv-Specific Phase 3 Notes

For `conv.mojo`, Phase 3 was applied to 6 functions — each requiring updates to:
- Return type annotation: `-> Conv2dBackwardResult:` → `-> GradientTriple:`
- Docstring Returns line: `Conv2dBackwardResult containing:` → `GradientTriple containing:`
- Return statement: `return Conv2dBackwardResult(...)` → `return GradientTriple(...)`

### Conv-Specific Phase 5 Notes (Layer File)

In `shared/core/layers/conv2d.mojo`, `Conv2dBackwardResult` appeared only in a comment
(not as an actual type annotation), so no concrete-type import was added — just the alias
import removed and the comment updated.

### Conv-Specific Phase 6 Notes (Partial Test Removal)

The backward-compat test file tested aliases for both Conv and Linear modules. Since only
Conv aliases were being removed in PR #3264, the file was partially updated (not deleted):
- Removed 4 Conv alias test functions and their imports
- Updated the `main()` runner and test count
- Linear alias tests were left intact

## Key Learnings

### Mojo-Specific: comptime Aliases

In Mojo, `comptime` aliases are compile-time type aliases (`comptime Foo = Bar`). These are NOT the same as Python type aliases. When removing:

- Replace with the RHS type (`GradientTriple`, `GradientPair`, `GradientQuad`)
- Delete the COMMENT block above the alias too
- Function return types, return statements, and docstrings all need updating

### replace_all is Safe for Mojo Type Names

Using `Edit` with `replace_all=True` on PascalCase type names is safe — no risk of substring collision. One pass handles signatures, docstrings, and body.

### Always Grep First, Then Read the Plan

An issue plan may describe removing 8 aliases from 6 files, but prior sessions may have already done most of the work. Always grep for remaining occurrences FIRST — the actual work may be a tiny fraction of what the plan describes.

### Worktree Branch May Already Be Partially Done

Before making changes in the main checkout, check if the worktree branch already has changes from a prior session. Changes in main checkout don't automatically appear in worktrees — copy files explicitly if needed.

## Results & Parameters

### Linear Module (Issue #3065, PR #3262)

| Parameter | Value |
| ----------- | ------- |
| Aliases removed | 2 (`LinearBackwardResult` → `GradientTriple`, `LinearNoBiasBackwardResult` → `GradientPair`) |
| Files modified | 3 (`linear.mojo`, `__init__.mojo`, `test_backward_compat_aliases.mojo`) |
| Net lines | -73 |

### Conv Module (Issue #3064, PR #3264)

| Parameter | Value |
| ----------- | ------- |
| Aliases removed | 6 (Conv2d, DepthwiseConv2d, DepthwiseSeparableConv2d variants) |
| Files modified | 4 (`conv.mojo`, `__init__.mojo`, `layers/conv2d.mojo`, `test_conv.mojo`) |
| Files deleted | 1 (`test_backward_compat_aliases.mojo`, 291 lines) |
| Replacement types | `GradientTriple`, `GradientPair`, `GradientQuad` |

### Grep Commands

```bash
# Find all DEPRECATED aliases in a module
grep -n "DEPRECATED" shared/core/<module>.mojo

# Find all alias usages
grep -rn "AliasName" --include="*.mojo" .

# Verify removal complete
grep -rn "AliasName" --include="*.mojo" . || echo "✓ All removed"
```

### Commit Message Pattern

```text
cleanup(<module>): remove deprecated <Module> backward result type aliases

Remove the N deprecated type aliases from shared/core/<module>.mojo:
- AliasName (replaced by CanonicalType)
...

Update all usages to use canonical types directly.
Remove alias exports from shared/core/__init__.mojo.
Remove/update backward-compat test file.

Closes #<issue-number>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Local `pixi run mojo build` | Ran mojo build locally to verify | GLIBC version incompatibility (`GLIBC_2.32/2.33/2.34` not found) — mojo requires newer glibc than available on the host | Mojo compilation must run in Docker container or CI; local verification is not possible on older Linux hosts |
| Deleting only alias definitions | Only removed the `comptime X = Y` lines, didn't search for usages | Function return types still referenced the removed alias, would cause compile errors | Always grep for all occurrences before removing — aliases appear in return types, docstrings, and test files |
| Grepping only code, not comments | Searched for aliases in code/imports only | Missed stale comments in test files that still referenced deprecated aliases | Grep with no type filter to catch alias names in comments too; verification grep must return 0 results across ALL file content |
| Assuming detailed plan means lots of work | Issue plan described removing 8 aliases from 6 files | All source/import changes had already been done by prior sessions; only 1 comment update remained | Always grep for remaining occurrences FIRST before reading the plan |
| Making changes in main checkout without checking worktree | Edited main checkout directly | Changes don't automatically appear in worktree branch — required manual copy | Always work in the worktree for the PR branch, or explicitly copy changed files |
| `replace_all` on already-handled aliases | Expected to find usages of `DepthwiseSeparableConv2dBackwardResult` | String not found — prior session had already applied the replacement in worktree | Check worktree branch state before applying changes; some may already be done |
| Adding `GradientTriple` import to `layers/conv2d.mojo` | Added `from shared.core.gradient_types import GradientTriple` because the old import included `Conv2dBackwardResult` | The type was only referenced in a comment, not in actual code — import was unnecessary | Check whether a type is used as an actual annotation before adding imports; comments don't need imports |
| Leaving layer file comment unchanged after alias removal | Left "The Conv2dBackwardResult struct is only movable" comment in place | Comment referenced the deleted type, causing confusion for future readers | Update all comments that reference removed type names, not just code usages |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3065, PR #3262 — Linear alias removal (2 aliases) | — |
| ProjectOdyssey | Issue #3064, PR #3264 — Conv alias removal (6 aliases) | — |
| ProjectOdyssey | Issue #3267, PR #3833 — Conv follow-up (stale comment cleanup) | — |

## Related Skills

- `type-alias-removal` - Python type alias removal workflow (different language, similar pattern)
- `backward-compat-removal` - General backward compatibility cleanup patterns
