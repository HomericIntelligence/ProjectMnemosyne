---
name: mojo-deprecated-alias-removal
description: 'Workflow for removing deprecated Mojo comptime type aliases and replacing
  usages with canonical types. Use when: removing DEPRECATED-marked comptime aliases
  from Mojo modules, cleaning up backward-compat test files, updating __init__.mojo
  exports after alias consolidation.'
category: architecture
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# Mojo Deprecated Alias Removal

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-05 |
| **Objective** | Remove deprecated `comptime` type aliases from Mojo modules and replace all usages with canonical types |
| **Outcome** | ✅ Successfully removed 2 Mojo comptime aliases, updated 3 files, PR created with auto-merge |
| **Issue** | #3065 - Remove deprecated Linear backward result type aliases |
| **PR** | #3262 |

## When to Use This Skill

Use this workflow when you need to:

- **Remove `DEPRECATED`-marked `comptime` aliases** from Mojo source files
- **Replace alias usages** with canonical gradient/result types throughout a module
- **Clean up backward-compat test files** that test the now-removed aliases
- **Update `__init__.mojo` exports** to remove alias re-exports
- **Consolidate gradient return types** (e.g., `LinearBackwardResult` → `GradientTriple`)

**Trigger Conditions:**

- Mojo file contains `comptime AliaName = CanonicalType` with `# DEPRECATED` comment
- Issue requests removing backward-compat aliases as cleanup phase
- Module exports both the alias and the canonical type
- A dedicated test file (`test_backward_compat_aliases.mojo`) tests the alias

## Verified Workflow

### Phase 1: Discovery

1. **Find all occurrences** of the deprecated alias names:

   ```bash
   grep -rn "LinearBackwardResult\|LinearNoBiasBackwardResult" --include="*.mojo" .
   ```

2. **Catalog all affected files** — typically 3 categories:
   - The source module defining the alias (e.g., `shared/core/linear.mojo`)
   - The package `__init__.mojo` re-exporting the alias
   - The backward-compat test file (`test_backward_compat_aliases.mojo`)

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

2. **Update function return types** in the same file:

   ```mojo
   # BEFORE
   fn linear_backward(...) raises -> LinearBackwardResult:

   # AFTER
   fn linear_backward(...) raises -> GradientTriple:
   ```

3. **Update return statements:**

   ```mojo
   # BEFORE
   return LinearBackwardResult(grad_input^, grad_kernel^, grad_bias^)

   # AFTER
   return GradientTriple(grad_input^, grad_kernel^, grad_bias^)
   ```

4. **Update docstrings** referencing the alias:

   ```mojo
   # BEFORE
   Returns:
       LinearBackwardResult containing: ...

   # AFTER
   Returns:
       GradientTriple containing: ...
   ```

### Phase 3: Update `__init__.mojo` Exports

Remove the alias names from the module's import/export block:

```mojo
# BEFORE
from shared.core.linear import (
    linear,
    linear_no_bias,
    linear_backward,
    linear_no_bias_backward,
    LinearBackwardResult,        # <-- Remove
    LinearNoBiasBackwardResult,  # <-- Remove
)

# AFTER
from shared.core.linear import (
    linear,
    linear_no_bias,
    linear_backward,
    linear_no_bias_backward,
)
```

### Phase 4: Update Backward-Compat Test File

The `test_backward_compat_aliases.mojo` file typically tests multiple aliases. Only remove tests for the aliases being deleted, preserve the rest:

1. **Remove alias imports:**

   ```mojo
   # BEFORE
   from shared.core import (
       LinearBackwardResult,
       LinearNoBiasBackwardResult,
       Conv2dBackwardResult,  # keep
       ...
   )

   # AFTER
   from shared.core import (
       Conv2dBackwardResult,  # keep
       ...
   )
   ```

2. **Remove test functions** for the deleted aliases entirely.

3. **Remove their calls from `main()`:**

   ```mojo
   fn main() raises:
       # test_linear_backward_result_alias()      <-- Remove
       # test_linear_no_bias_backward_result_alias()  <-- Remove
       test_conv2d_backward_result_alias()        # keep
   ```

4. **Update the test count** in the final print statement:

   ```mojo
   # BEFORE
   print("\n✓ All 8 backward compatibility comptime tests passed\n")

   # AFTER
   print("\n✓ All 6 backward compatibility comptime tests passed\n")
   ```

5. **Clean up stale comments** that reference removed aliases in remaining functions.

### Phase 5: Verification

1. **Confirm no alias references remain:**

   ```bash
   grep -rn "LinearBackwardResult\|LinearNoBiasBackwardResult" --include="*.mojo" .
   # Expected: No matches
   ```

2. **Build the shared package** (requires Docker in this repo due to GLIBC requirements):

   ```bash
   just docker-run pixi run mojo build shared
   # OR let CI validate via PR
   ```

3. **Run the linear tests** (via CI or Docker):

   ```bash
   pixi run mojo test tests/shared/core/test_linear.mojo
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Local `pixi run mojo build` | Ran mojo build locally to verify | GLIBC version incompatibility (`GLIBC_2.32/2.33/2.34` not found) — mojo requires newer glibc than available on the host | Mojo compilation must run in Docker container or CI; local verification is not possible on older Linux hosts |
| Deleting only alias definitions | Only removed the `comptime X = Y` lines, didn't search for usages | Function return types still referenced the removed alias, would cause compile errors | Always grep for all occurrences before removing — aliases appear in return types, docstrings, and test files |
| Grepping only code, not comments | On follow-up issue #3267, only searched for aliases in code/imports | Missed one stale comment in `test_conv.mojo` that still referenced `Conv2dBackwardResult` — the plan said 18+ changes but prior sessions had done all the real work already | Grep with no `--include` type filter to catch alias names in comments too; the final verification grep must return 0 results across ALL file content |
| Assuming a detailed plan means lots of work remains | Issue #3267 plan described removing 8 aliases from 6 files; assumed this was all unimplemented | All source/import changes had already been done by prior sessions; only 1 comment update remained | Always grep for remaining occurrences FIRST before reading the plan — the actual work may be a tiny fraction of what the plan describes |

## Results & Parameters

### Files Modified

```text
shared/core/linear.mojo                          -13 lines (alias defs + usages)
shared/core/__init__.mojo                         -2 lines (alias exports)
tests/shared/core/test_backward_compat_aliases.mojo  -73 lines (2 test functions + imports)
```

### Grep Commands

```bash
# Find all alias usages
grep -rn "LinearBackwardResult\|LinearNoBiasBackwardResult" --include="*.mojo" .

# Verify removal complete
grep -rn "LinearBackwardResult\|LinearNoBiasBackwardResult" --include="*.mojo" . || echo "✓ All removed"

# Find all DEPRECATED aliases in a module (for discovery)
grep -n "DEPRECATED" shared/core/linear.mojo
```

### Commit Message Pattern

```text
cleanup(linear): remove deprecated LinearBackwardResult type aliases

Remove the 2 deprecated type aliases from shared/core/linear.mojo:
- LinearBackwardResult (replaced by GradientTriple)
- LinearNoBiasBackwardResult (replaced by GradientPair)

Update all usages in linear.mojo to use canonical types directly.
Remove alias exports from shared/core/__init__.mojo.
Remove linear alias tests from test_backward_compat_aliases.mojo.

Closes #<issue-number>
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3065, PR #3262 — initial linear alias removal | [notes.md](../references/notes.md) |
| ProjectOdyssey | Issue #3267, PR #3833 — follow-up: remaining conv2d aliases (all already removed; only 1 stale comment remained) | [notes-3267.md](../references/notes-3267.md) |

## Related Skills

- `type-alias-removal` - Python type alias removal workflow (different language, similar pattern)
- `backward-compat-removal` - General backward compatibility cleanup patterns
