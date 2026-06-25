---
name: mojo-srp-module-split-bottom-import
description: "Use when: (1) a Mojo file exceeds ~3,000 lines and needs SRP extraction into sibling modules in the same package directory, (2) you are splitting any_tensor.mojo or a similarly large Mojo module and need to avoid circular import type-identity issues, (3) you encounter 'type registered twice' or silent type-mismatch errors after placing sibling module imports at the top of a Mojo file, (4) you need to determine how many lines of Mojo code remain after mojo format runs (formatter adds whitespace that can push line counts over budget), (5) you want to access private struct fields from a sibling module within the same package."
category: architecture
date: 2026-06-20
version: "1.0.0"
user-invocable: false
tags: [mojo, srp, module-split, circular-import, bottom-of-file, refactoring, any-tensor]
---

# Mojo SRP Module Split with Bottom-of-File Imports

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-20 |
| **Objective** | Canonical procedure for splitting large Mojo files (>3,000 lines) into sibling modules while avoiding circular import type-identity issues via the bottom-of-file import pattern |
| **Outcome** | Verified on ProjectOdyssey Issue #5182 — `any_tensor.mojo` 4,241-line SRP extraction into 6 sibling modules; the bottom-of-file import pattern is required in Mojo 1.0 to prevent type registration duplication |
| **Verification** | verified-local |

## When to Use

1. A Mojo file exceeds ~3,000 lines and has identifiable functional clusters (ops, printing, indexing, dtype conversion, views)
2. Splitting `any_tensor.mojo` or any large Mojo module into sibling modules in the same package directory
3. You encounter silent type-mismatch errors or "type registered twice" after placing sibling module imports at the top of a file
4. You need an accurate post-format line count to verify budget compliance (formatter adds whitespace)
5. You need cross-module access to `_private` struct fields within the same package

## Verified Workflow

### Quick Reference

```bash
# Verify the package still builds after each extraction step
pixi run mojo package src/projectodyssey/ --Werror

# Format ALL changed files before counting lines against budget
pixi run mojo format src/projectodyssey/tensor/any_tensor.mojo
pixi run mojo format src/projectodyssey/tensor/tensor_ops.mojo

# Count lines AFTER formatting (formatter adds whitespace)
wc -l src/projectodyssey/tensor/any_tensor.mojo

# Run full test suite to catch regressions
just test-mojo
```

### The Bottom-of-File Import Rule (Most Important Rule)

**NEVER put new sibling module imports at the TOP of the original file.**
**ALWAYS place them at the BOTTOM — after all struct and function definitions.**

```mojo
# ❌ WRONG — top-of-file sibling import creates type-identity issues
from . import tensor_ops
from . import tensor_printing

struct AnyTensor:
    # ... all definitions ...
```

```mojo
# ✅ CORRECT — bottom-of-file import after all definitions
struct AnyTensor:
    # ... all definitions ...

fn some_top_level_fn():
    # ... all top-level functions ...

# ---- BOTTOM OF FILE: sibling module imports ----
from . import tensor_ops
from . import tensor_printing
from . import tensor_io
```

### Why the Bottom-of-File Rule Exists

Top-of-file imports of sibling modules that themselves import types from the current file
create type-identity issues in Mojo 1.0. The same type gets registered twice — once per
import direction — causing subtle type mismatch errors at call sites. The bottom-of-file
pattern breaks the cycle by ensuring all type definitions are fully complete before sibling
imports are resolved. This is distinct from the **function-body import** approach (which
works for a single function); use bottom-of-file imports when a module needs many helpers
from a sibling.

**Evidence in ProjectOdyssey**: `src/projectodyssey/tensor/any_tensor.mojo` at ~line 4080+
already uses this pattern with bottom-of-file imports for `tensor_io`, `creation`, and
`utils` modules.

### Cross-Module Private Field Access

Mojo uses **package-scoped** privacy, not struct-scoped. Sibling modules in the same package
directory **CAN** access `_private` fields of structs defined in other modules in the same
package. Before assuming cross-module private access won't work, grep for existing call sites:

```bash
grep -rn "\._data\b\|\._shape\b\|\._strides\b" src/projectodyssey/tensor/ --include="*.mojo"
```

If existing sibling modules already access `_private` fields, new sibling modules can too.

### Extraction Clusters (any_tensor.mojo Reference)

When splitting `any_tensor.mojo` (Issue #5182), cluster functions by functional theme:

| New Module | Size | Contents |
| --- | --- | --- |
| `tensor_ops.mojo` | ~318 lines | binary/unary/compare op helpers, matmul, broadcast |
| `tensor_printing.mojo` | ~219 lines | write_to, format_element, format_nd_slice, write_repr |
| `tensor_split.mojo` | ~100 lines | split and split_with_indices helpers |
| `tensor_indexing.mojo` | ~258 lines | slice normalization and _getitem_*_impl helpers |
| `tensor_dtype_conv.mojo` | ~481 lines | FP8/BF8/int dtype conversion, block quant conversions |
| `tensor_views.mojo` | ~357 lines | slice, transpose, clone, diff, reshape, array_equal helpers |

### Step-by-Step Procedure

1. Identify extraction clusters by functional theme — grep for related function names to find natural boundaries
2. Create new sibling `.mojo` file(s) in the same package directory (e.g., `src/projectodyssey/tensor/`)
3. Move the impl functions/structs to the new file
4. Add necessary imports at the **TOP** of the **NEW** sibling file (standard top-of-file imports are fine in the new file)
5. Add `from . import <new_module>` at the **BOTTOM** of the original file — after all definitions
6. Build: `pixi run mojo package src/<package>/ --Werror`
7. Run `mojo format` on all changed files
8. Recount lines in the original file — adjust if formatter pushed you over budget (trim verbose docstrings, not code)
9. Run full test suite: `just test-mojo`

### Line Count Budget After Format

Always run `mojo format` BEFORE counting lines against your target. The formatter adds
blank lines between struct methods, after decorators, and around trait blocks. A file
targeting 3,000 lines may land at 3,200 after formatting. Compensate by trimming verbose
docstrings (not code) or moving additional helpers to sibling modules.

```bash
# Check line count after format
pixi run mojo format src/projectodyssey/tensor/any_tensor.mojo
wc -l src/projectodyssey/tensor/any_tensor.mojo
# If over budget, identify verbose docstrings to trim:
grep -n '"""' src/projectodyssey/tensor/any_tensor.mojo | head -40
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Top-of-file sibling imports | Placed `from . import tensor_ops` at the top of `any_tensor.mojo` | Type-identity issues in Mojo 1.0 — types (e.g., AnyTensor) registered twice, once per import direction, causing silent type mismatch errors at call sites | Place sibling imports at the BOTTOM of the file — after all struct and function definitions |
| Extract variadic `*Slice` `__getitem__` overload | Attempted to move the variadic multi-index `__getitem__(*args: Slice)` overload to a sibling module | Requires direct access to Mojo compiler internals for variadic slice dispatch; cannot be delegated across module boundaries | Leave the variadic `*Slice` overload inlined in the original file with a comment: `# Inlined per #5182: variadic *Slice overload requires compiler internals` |
| Counting lines before mojo format | Targeted <3,000 lines in the source, verified count, then ran formatter | Mojo formatter added ~200 lines of whitespace (blank lines between methods, around traits), pushing the file over budget after commit | Always run `mojo format` first, then count lines; plan a ~10% whitespace buffer in budgets |
| Assuming cross-module private access fails | Skipped extracting helpers that accessed `_data`/`_shape` assuming Mojo would block it | Mojo uses package-scoped (not struct-scoped) privacy; sibling modules CAN access `_private` fields | grep for existing cross-module private field access first; if sibling modules already use `._data`, new ones can too |

## Results & Parameters

### Critical Rules Summary

```yaml
bottom_of_file_rule: "ALWAYS place sibling module imports after all definitions in the original file"
why_bottom:          "Top-of-file sibling imports → type registered twice → type mismatch errors in Mojo 1.0"
package_privacy:     "Mojo uses package-scoped privacy; siblings CAN access _private fields"
format_first:        "Run mojo format BEFORE counting lines; formatter adds ~10% whitespace"
verification_cmd:    "pixi run mojo package src/projectodyssey/ --Werror"
leave_inlined:       "Variadic *Slice __getitem__ overloads — cannot extract across module boundaries"
```

### any_tensor.mojo Extraction Targets (Issue #5182)

| Cluster | Target File | Estimated Lines | Status |
| --- | --- | --- | --- |
| Binary/unary/compare ops | `tensor_ops.mojo` | ~318 | Extractable |
| Printing/repr helpers | `tensor_printing.mojo` | ~219 | Extractable |
| Split/split_with_indices | `tensor_split.mojo` | ~100 | Extractable |
| Slice normalization + getitem impls | `tensor_indexing.mojo` | ~258 | Extractable |
| FP8/BF8/int dtype conversions | `tensor_dtype_conv.mojo` | ~481 | Extractable |
| Slice/transpose/clone/reshape | `tensor_views.mojo` | ~357 | Extractable |
| Variadic `*Slice __getitem__` | (stays in any_tensor.mojo) | ~30 | Leave inlined |

### Verified Build Commands

```bash
# Single-package verification (fast, catches import/type errors)
pixi run mojo package src/projectodyssey/ --Werror

# Full test suite (slower, catches behavioral regressions)
just test-mojo

# Format all changed .mojo files (run BEFORE line count)
pixi run mojo format src/projectodyssey/tensor/any_tensor.mojo
pixi run mojo format src/projectodyssey/tensor/tensor_ops.mojo
```

### Bottom-of-File Import Template

```mojo
# ==============================================================================
# Sibling module imports — placed at BOTTOM to avoid Mojo 1.0 type-identity
# issues that occur when mutual imports are placed at the top of the file.
# See: Issue #5182, ADR-014
# ==============================================================================
from . import tensor_ops
from . import tensor_printing
from . import tensor_split
from . import tensor_indexing
from . import tensor_dtype_conv
from . import tensor_views
```
