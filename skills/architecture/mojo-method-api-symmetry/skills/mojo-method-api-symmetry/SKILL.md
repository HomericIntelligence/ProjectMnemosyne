---
name: mojo-method-api-symmetry
description: "Add thin method wrappers to Mojo structs to complete API symmetry with free functions. Use when: (1) a free function was exported but no struct method wrapper exists, (2) closing follow-up API symmetry issues after a larger feature PR, (3) auditing a struct for missing parity with module-level functions."
category: architecture
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Pattern** | Thin method wrappers on Mojo structs |
| **Problem** | Free functions exported from a module but no corresponding `self.method()` API on the struct |
| **Solution** | Add inline-import delegation methods after the last method in the struct |
| **Risk** | Low — no logic duplication, methods just call the free function |
| **Test strategy** | 5-function test file (ADR-009 ≤10 fn limit), symmetry test verifies method == free function |

## When to Use

- A follow-up issue says "only `split` got a method wrapper but `split_with_indices` was also exported"
- PR review feedback notes missing `.method()` counterpart for a module-level `fn`
- Auditing a struct for API completeness against its companion module functions
- Closing "API symmetry" or "method wrapper" issues

## Verified Workflow

### Quick Reference

```bash
# 1. Find what's exported from the module
grep -n "split\|tile\|repeat" shared/core/__init__.mojo

# 2. Find what methods already exist on the struct
grep -n "^    fn " shared/core/extensor.mojo | grep -E "split|tile|repeat"

# 3. Find the last method in the struct (insertion point)
grep -n "^    fn \|^fn \|^struct " shared/core/extensor.mojo | tail -20

# 4. Check assert_value_at signature to avoid type errors
grep -n "fn assert_value_at" shared/testing/assertions.mojo
```

### Step 1 — Identify missing wrappers

Read the issue and the module's `__init__.mojo` to list everything exported. Then grep the
struct for existing `fn` methods. The difference is the set of missing wrappers.

```bash
grep -n "split\|tile\|repeat\|permute" shared/core/__init__.mojo
grep -n "^    fn split\|^    fn tile" shared/core/extensor.mojo
```

### Step 2 — Find the insertion point

Insert new methods just before the closing of the struct (before the blank line + standalone
`fn` section). The last struct method is a reliable anchor for the edit.

```bash
grep -n "^    fn \|^fn \|^struct " shared/core/extensor.mojo | tail -30
```

### Step 3 — Write the method using inline imports

Follow the pattern of existing wrappers like `broadcast_to`. Use an inline import inside the
method body to avoid circular import issues at the module level.

```mojo
fn split_with_indices(
    self, split_indices: List[Int], axis: Int = 0
) raises -> List[ExTensor]:
    """Split tensor at specified indices along an axis.

    Method wrapper for the module-level `split_with_indices()` function.

    Args:
        split_indices: List of indices where to split (e.g., [3, 7]
            creates 3 sections).
        axis: Axis along which to split (default: 0).

    Returns:
        List of ExTensor objects resulting from splits.

    Raises:
        Error: If axis is invalid or indices are out of bounds/unordered.

    Example:
    ```mojo
        var a = arange(0.0, 10.0, 1.0, DType.float32)
        var parts = a.split_with_indices([3, 7])
    ```
    """
    from shared.core.shape import split_with_indices as split_with_indices_fn

    return split_with_indices_fn(self, split_indices, axis)
```

### Step 4 — Write tests respecting ADR-009

Mojo v0.26.1 has a heap corruption bug that triggers with >10 `fn test_` functions per file.
Keep test files to ≤10 functions (ADR-009).

```mojo
# ADR-009: This file is intentionally limited to ≤10 fn test_ functions.
```

Key symmetry test pattern — verify method output matches free function:

```mojo
fn test_split_with_indices_method_vs_free_fn() raises:
    """Test that method result matches free function result (symmetry test)."""
    var a = arange(0.0, 10.0, 1.0, DType.float32)
    var indices = List[Int]()
    indices.append(3)
    indices.append(7)

    var method_parts = a.split_with_indices(indices)
    var free_parts = split_with_indices(a, indices)

    if len(method_parts) != len(free_parts):
        raise Error("Method and free function should return same number of parts")

    for i in range(len(method_parts)):
        if method_parts[i].numel() != free_parts[i].numel():
            raise Error("Part sizes should match between method and free function")
```

### Step 5 — Use `message=` keyword for assert_value_at

The `assert_value_at` signature is `(tensor, index, expected, tolerance, message)`. Passing
a string as the 4th positional arg will fail because Mojo tries to convert it to `Float64`.
Always use the `message=` keyword argument:

```mojo
# ❌ WRONG — string interpreted as tolerance: Float64
assert_value_at(parts[0], 0, 0.0, "should be 0.0")

# ✅ CORRECT — message= keyword bypasses the tolerance parameter
assert_value_at(parts[0], 0, 0.0, message="should be 0.0")
```

### Step 6 — Run tests and commit

```bash
# Run with explicit PIXI_PROJECT_MANIFEST when in a worktree
PIXI_PROJECT_MANIFEST=/path/to/worktree/pixi.toml pixi run mojo tests/shared/core/test_extensor_method_api.mojo

# Commit with SKIP=mojo-format if on incompatible GLIBC host
SKIP=mojo-format git commit -m "feat(extensor): add split_with_indices method wrapper"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Passing message as 4th positional arg to `assert_value_at` | Called `assert_value_at(tensor, idx, 0.0, "message")` | Mojo tried to convert `StringLiteral` to `Float64` for the `tolerance` parameter | Always use `message=` keyword argument; check function signature before writing tests |
| Running `pixi run mojo test` | Used `mojo test` subcommand | Mojo v0.26.1 has no `test` subcommand; only `mojo <file>` works | Use `pixi run mojo <file>` directly to run test files |

## Results & Parameters

**What was implemented (PR #4803):**

- `ExTensor.split(num_splits, axis=0)` — thin wrapper for `shared.core.shape.split()`
- `ExTensor.split_with_indices(split_indices, axis=0)` — thin wrapper for `shared.core.shape.split_with_indices()`

**Test file structure:**

```
tests/shared/core/test_extensor_method_api.mojo
├── test_split_method_equal()          # 1D equal split, value verification
├── test_split_method_axis()           # 2D split along axis=1
├── test_split_with_indices_method_basic()  # 1D split at [3,7]
├── test_split_with_indices_method_2d()     # 2D split along axis=0
└── test_split_with_indices_method_vs_free_fn()  # symmetry test
```

**Commit flag for GLIBC-incompatible hosts:**

```bash
SKIP=mojo-format git commit -m "feat(extensor): ..."
```

**PR creation:**

```bash
gh pr create --title "feat(extensor): add split_with_indices method wrapper" \
  --body "$(cat <<'EOF'
## Summary
...
Closes #<issue>
EOF
)" --label "implementation"
gh pr merge --auto --rebase <PR_NUMBER>
```
