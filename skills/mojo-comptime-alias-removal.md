---
name: mojo-comptime-alias-removal
description: 'Remove deprecated Mojo comptime type aliases and update all usages to
  direct types. Use when: removing `comptime Alias = Type` backward-compat aliases
  from Mojo source files.'
category: architecture
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# Mojo Comptime Alias Removal Workflow

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-05 |
| **Objective** | Remove 6 deprecated `comptime` type aliases from `shared/core/conv.mojo` and update all usages to use `GradientTriple`, `GradientPair`, `GradientQuad` directly |
| **Outcome** | All 6 aliases removed, 5 files updated, pre-commit hooks pass, PR #3264 created |
| **Issue** | #3064 - [Cleanup] Remove deprecated Conv backward result type aliases |

## When to Use

Use this workflow when you need to:

- Remove `comptime AliasName = ConcreteType` definitions from Mojo files
- Update function return types, docstrings, and return statements after alias removal
- Remove alias exports from `__init__.mojo` module files
- Remove tests that validated the removed aliases
- Update comments that reference the old alias names

**Trigger Conditions:**

- Mojo source has lines like `comptime OldName = NewType` marked `DEPRECATED`
- Issue asks to "remove deprecated type aliases" from a specific file/line range
- Type consolidation PR has landed and backward-compat aliases are now safe to remove

## Verified Workflow

### Phase 1: Discovery

1. **Find all alias definitions** using Grep:

   ```bash
   grep -rn "comptime.*BackwardResult\|AliasName" shared/ tests/ --include="*.mojo"
   ```

2. **Identify all usage locations** - there will be 4+ categories:
   - The source file defining the aliases (function signatures, return statements, docstrings)
   - Module `__init__.mojo` exports
   - Layer files that import specific aliases
   - Test files that test backward-compat aliases

3. **Map each alias to its replacement type**:

   | Deprecated Alias | Replacement Type |
   | ----------------- | ----------------- |
   | `OldName` | `NewType` |

### Phase 2: Remove Alias Definitions

In the source `.mojo` file, delete the entire alias block including comments:

```mojo
# BEFORE (delete all of this):
# Backward compatibility aliases using generic gradient containers
# DEPRECATED: Use GradientTriple directly instead of Conv2dBackwardResult
comptime Conv2dBackwardResult = GradientTriple

# DEPRECATED: Use GradientPair directly instead of Conv2dNoBiasBackwardResult
comptime Conv2dNoBiasBackwardResult = GradientPair
```

### Phase 3: Update Function Signatures and Bodies in Source File

For each function that returns an alias type, update:

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

### Phase 4: Update Module Exports

In `__init__.mojo`, remove the alias names from the import/export block:

```mojo
# BEFORE
from shared.core.conv import (
    conv2d_backward,
    Conv2dBackwardResult,          # Remove
    Conv2dNoBiasBackwardResult,    # Remove
    depthwise_conv2d_backward,
    DepthwiseConv2dBackwardResult, # Remove
)

# AFTER
from shared.core.conv import (
    conv2d_backward,
    depthwise_conv2d_backward,
)
```

### Phase 5: Update Layer Files That Import Aliases

For files that import an alias to use in type annotations or code:

```mojo
# BEFORE
from shared.core.conv import conv2d, conv2d_backward, Conv2dBackwardResult

# AFTER (if alias is only used in comments, just remove it)
from shared.core.conv import conv2d, conv2d_backward
```

If the alias is used as an actual type annotation in the layer file, replace it with the
concrete type and add a direct import:

```mojo
from shared.core.gradient_types import GradientTriple
```

But only add this import if the type is actually used as a type annotation (not just in comments).

### Phase 6: Update Tests

**For backward-compat alias test files**: Remove test functions for the deleted aliases and
their imports. Update the main runner count:

```mojo
# BEFORE
from shared.core import (
    Conv2dBackwardResult,       # Remove
    Conv2dNoBiasBackwardResult, # Remove
    ...
)

fn main() raises:
    test_conv2d_backward_result_alias()       # Remove
    test_conv2d_no_bias_backward_result_alias() # Remove
    print("\n All 8 tests passed\n")  # Update count
```

**For files with comments referencing old alias names**: Update comments to use the
concrete type name:

```mojo
# BEFORE
# NOTE: Backward tests disabled due to ownership issues in Conv2dBackwardResult.
# TODO(#2724): Fix Conv2dBackwardResult ownership to enable backward pass testing

# AFTER
# NOTE: Backward tests disabled due to ownership issues in GradientTriple.
# TODO(#2724): Fix GradientTriple ownership to enable backward pass testing
```

### Phase 7: Verify No References Remain

```bash
# Should only find references in the prompt/issue file
grep -rn "OldAliasName" shared/ tests/ --include="*.mojo"
```

### Phase 8: Run Checks

```bash
# Build (if Mojo available)
pixi run mojo build shared

# Test (if Mojo available)
pixi run mojo test tests/shared/core/test_conv.mojo

# Pre-commit hooks (always run these)
pixi run pre-commit run --all-files
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Adding `GradientTriple` import to `layers/conv2d.mojo` | Added `from shared.core.gradient_types import GradientTriple` because the old import included `Conv2dBackwardResult` | The type is only used in a comment, not in actual code | Check whether a type is used as an actual annotation before adding imports; comments don't need imports |
| Leaving layer file comment unchanged | Left "The Conv2dBackwardResult struct is only movable" comment | Comment references deleted type, causing confusion | Update all comments that reference removed type names |

## Results & Parameters

### Files Modified Pattern

For a typical conv alias removal across 5 files:

```text
shared/core/conv.mojo              - Remove alias definitions, update 6 functions
shared/core/__init__.mojo          - Remove 6 alias exports from import block
shared/core/layers/conv2d.mojo     - Remove alias import, update comment
tests/shared/core/test_backward_compat_aliases.mojo - Remove 4 test functions + imports
tests/shared/core/test_conv.mojo   - Update 2 comments
```

### Commit Message Template

```
cleanup(conv): remove deprecated Conv backward result type aliases

Remove the N deprecated comptime type aliases from <path/to/file.mojo>
and update all usages to use GradientTriple, GradientPair, GradientQuad directly.

Changes:
- Removed N deprecated aliases: AliasA, AliasB, ...
- Updated function return types in source.mojo
- Removed alias exports from shared/core/__init__.mojo
- Removed AliasImport import from layers/layer.mojo
- Removed alias tests from test_backward_compat_aliases.mojo
- Updated comments in test file to reference concrete types

Closes #NNNN
```

### Key Mojo-Specific Notes

- `comptime` aliases in Mojo are not the same as Python type aliases - they're compile-time
  constants, so removing them removes the name entirely (no runtime impact)
- Since `comptime Alias = ConcreteType` means the alias IS the concrete type, return statements
  like `return Alias(...)` become `return ConcreteType(...)` - functionally identical
- Mojo does not have `__all__` like Python - module exports are controlled by what's imported
  in `__init__.mojo`; removing an alias from that file removes it from the public API

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3064, PR #3264 | [notes.md](../references/notes.md) |

## Related Skills

- `type-alias-removal` - Same pattern for Python codebases
- `backward-compat-removal` - Removing deprecated backward-compat shims
