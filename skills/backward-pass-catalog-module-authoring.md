---
name: backward-pass-catalog-module-authoring
description: 'Add a new module section to backward-pass-catalog.md documenting backward
  passes with formulas, shapes, and stability notes. Use when: an issue asks to document
  formulas/shapes for an untracked backward function, or catalog header stats are
  stale after new functions are implemented.'
category: documentation
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
| ----------- | ------- |
| **Skill Name** | backward-pass-catalog-module-authoring |
| **Category** | documentation |
| **Language** | Markdown |
| **Issue Type** | Catalog documentation, backward pass coverage |
| **Resolution** | Add MODULE N section + update header stats + add Summary Table rows |

## When to Use

1. A GitHub issue asks to add a catalog entry for a backward pass function not yet in
   `docs/dev/backward-pass-catalog.md`
2. A new module has been implemented and needs to be documented alongside existing modules
3. The "Known Test Pathologies" cross-reference mentions a section that doesn't exist yet
4. The header stats (total functions, module count) are stale after implementation
5. A follow-up issue from a test-gotcha issue asks for formula documentation

## Verified Workflow

### Quick Reference

| Step | Action | Tool |
| ------ | -------- | ------ |
| 1 | Locate the `.mojo` source for accurate signatures and line numbers | `Glob` + `Grep` |
| 2 | Read the full docstring for formulas | `Read` |
| 3 | Edit catalog: header stats | `Edit` |
| 4 | Edit catalog: insert MODULE N before Summary Table | `Edit` |
| 5 | Edit catalog: add rows to Summary Table | `Edit` |
| 6 | Edit catalog: update Training Readiness checklist | `Edit` |
| 7 | Update Known Test Pathologies cross-reference | `Edit` |
| 8 | Run pre-commit (markdownlint) | `Bash` |

### Step 1: Find the source implementation

Use `Glob` to locate the module, then `Grep` to find the function signature and line number:

```bash
grep -n "fn batch_norm2d_backward\|fn layer_norm_backward" shared/core/normalization.mojo
```

Read the full docstring — it usually contains the mathematical formulation and reference
links needed for the catalog entry.

### Step 2: Determine the next MODULE number

Read the catalog header:

```text
**Total Backward Functions**: 27 across 5 modules
```

The new module gets the next number (`MODULE 6`).

### Step 3: Update the catalog header stats

Find:

```text
**Total Backward Functions**: 27 across 5 modules
**Broadcasting Support**: 9/27 functions (arithmetic, reductions)
**Numerical Stability**: 10/27 functions
**Activation Functions**: 7/27
```

Update the counts by adding the new function count. If 2 functions are added:

- `27 → 29` total, `5 → 6` modules
- Broadcasting fraction denominator updates (9/27 → 9/29)
- Stability fraction updates (add 2 if both use epsilon)

### Step 4: Insert the MODULE section before the Summary Table

The insertion point is the `## SUMMARY TABLE:` heading. Structure the module section as:

```markdown
## MODULE N: FILENAME.MOJO

**Module Overview**: One-line description
**Total Backward Functions**: N

### 1. function_name_backward

**Location**: `path/to/file.mojo` line NNN
**Signature**:

` `` `mojo
fn function_name_backward(
    ...
) raises -> ReturnType
` `` `

**Return Type**: `ReturnType` — description of each element

**Purpose**: What this computes.

### Input Shapes

- `param_name`: `(shape)` — description

### Output Shapes

- `output_name`: `(shape)` — description

### Mathematical Formula

` `` `text
Forward pass:
    ...

Backward pass:
    ...
` `` `

### Numerical Stability

- Epsilon (default `1e-5`) added inside `sqrt` to prevent division by zero
- Recommended tolerances: `rtol=1e-2`, `atol=1e-5`

### References

- Author (Year). Title. URL

---
```

For normalization functions, always include:
- **Training vs Inference mode** comparison (if applicable)
- **Kratzert Formula Note** linking to Known Test Pathologies
- **Key Differences table** (if documenting two related functions)
- **Dtype support** (normalization often drops float16)

### Step 5: Add rows to the Summary Table

Find the last row before `---` after the table and append:

```markdown
| normalization | batch_norm2d_backward | 1 | NO | epsilon/Float32 | NO | High |
| normalization | layer_norm_backward | 2 | NO | epsilon/Float32 | NO | High |
```

Column meanings: `Module | Function | Count-in-module | Broadcasting | Stability | Shape-Reduction | Complexity`

### Step 6: Update Training Readiness checklist

Add a new `[x]` line:

```markdown
- [x] **Normalization backward passes supported**: batch_norm2d, layer_norm (see MODULE 6)
```

Also update the Training Readiness Conclusion bullet if it mentions normalization.

### Step 7: Update Known Test Pathologies cross-reference

If the pathologies section has a `**See also**: ...` line, point it at the new MODULE:

```markdown
**See also**: MODULE 6 — `batch_norm2d_backward` and `layer_norm_backward` entries above for
formula documentation, dtype support, and recommended gradient-check tolerances.
```

### Step 8: Validate

```bash
pixi run pre-commit run --files docs/dev/backward-pass-catalog.md
```

All hooks must pass. Common failures:

- Blank lines required before/after fenced code blocks
- Language tag required on every code block
- Lines ≤ 120 characters

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Guessing signatures from memory | Wrote the function signature without reading the .mojo source | Line numbers and parameter names were wrong (e.g., `GradientTriple` vs `Tuple[ExTensor, ExTensor, ExTensor]`) | Always read the actual `.mojo` source — use `Grep` for line number, then `Read` the docstring |
| Updating header denominator inconsistently | Updated total count but not the fractions | Broadcasting and stability fractions showed wrong denominators | Update ALL four header stat lines atomically in one Edit call |
| Inserting MODULE section after Summary Table | Placed the new module at end of file | Breaks reading flow — catalog is organized by module before the summary | Always insert before `## SUMMARY TABLE:` |
| Using `## Quick Reference` as top-level section | Preserved source skill's Quick Reference at top level | Violates SKILL.md structure — must be `### Quick Reference` inside `## Verified Workflow` | Demote Quick Reference to subsection of Verified Workflow |

## Results & Parameters

### Files Modified

| File | Edits Made |
| ------ | ----------- |
| `docs/dev/backward-pass-catalog.md` | Header stats, MODULE 6 section (2 functions), Summary Table rows, Training Readiness checklist, Known Test Pathologies cross-reference |

### Catalog Entry Template for Normalization Functions

```markdown
## MODULE N: NORMALIZATION.MOJO

**Module Overview**: Batch and layer normalization with mean-centering backward passes
**Total Backward Functions**: 2

### 1. batch_norm2d_backward

**Location**: `shared/core/normalization.mojo` line NNN
**Return Type**: `Tuple[ExTensor, ExTensor, ExTensor]` — `(grad_input, grad_gamma, grad_beta)`

### Mathematical Formula (Training Mode)

` `` `text
N_spatial = batch * height * width
grad_x_norm = grad_output * gamma
grad_var = sum(grad_x_norm * (x-mean) * -0.5 * (var+eps)^(-3/2))  shape: (C,)
grad_mean = sum(grad_x_norm * -1/std) + grad_var * mean(-2(x-mean))
grad_input = grad_x_norm / std + grad_var * 2(x-mean)/N_spatial + grad_mean/N_spatial

grad_gamma = sum(grad_output * x_norm, axes=[N, H, W])
grad_beta  = sum(grad_output,          axes=[N, H, W])
` `` `
```

### Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3872, PR #4817 | [notes.md](../references/notes.md) |
