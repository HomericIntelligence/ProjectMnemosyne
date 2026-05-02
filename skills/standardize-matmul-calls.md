---
name: standardize-matmul-calls
description: 'Convert A.__matmul__(B) dunder method calls to matmul(A, B) function
  syntax. Use when: codebase has mixed matmul call patterns or standardizing operator
  syntax in Mojo ML code.'
category: architecture
date: 2026-03-04
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | standardize-matmul-calls |
| **Category** | architecture |
| **Language** | Mojo |
| **Scope** | Test files, application code using `__matmul__` dunder calls |

## When to Use

- Codebase has mixed `A.__matmul__(B)` and `matmul(A, B)` patterns
- Standardizing dunder method calls to explicit function syntax
- Responding to GitHub issues requesting matmul call site consistency
- Code review reveals direct dunder method invocations that should be function calls

## Verified Workflow

1. **Search for call sites** (not definitions):

   ```bash
   grep -rn "__matmul__" --include="*.mojo" tests/ shared/ papers/
   ```

2. **Distinguish call sites from definitions**:

   - **Convert**: `A.__matmul__(B)` in test/application code (call sites)
   - **Leave unchanged**: `fn __matmul__(self, other: ...)` method definitions
   - **Leave unchanged**: `a @ b` operator syntax in tests specifically testing the `@` operator
   - **Leave unchanged**: docstring/comment references like `"a @ b should work via __matmul__"`

3. **Check imports before replacing**:

   ```bash
   grep -n "from shared.core.matrix import matmul" <file>
   ```

   If `matmul` is not imported, add the import. In this codebase it was already present in both affected functions.

4. **Preserve operand order** — `A.__matmul__(B)` → `matmul(A, B)` (A is left operand, B is right):

   ```mojo
   # Before
   var hidden = data.__matmul__(weights1)

   # After
   var hidden = matmul(data, weights1)
   ```

5. **Verify no `__matmul__` call sites remain**:

   ```bash
   grep -rn "\.__matmul__(" --include="*.mojo" tests/ shared/ papers/
   ```

6. **Commit with conventional commit format**:

   ```text
   refactor(tests): standardize matmul calls to function syntax
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Modifying definition in extensor.mojo | Considered changing `fn __matmul__` | Not a call site; removing it would break `@` operator | Only convert call sites, not definitions |
| Modifying test_dunder_matmul | Considered rewriting `a @ b` test | The test specifically validates `@` operator; comments referencing `__matmul__` are documentation | Skip tests whose purpose is testing the dunder/operator directly |

## Results & Parameters

**Files changed in this session**:

- `tests/shared/integration/test_packaging.mojo`
  - Line 408: `data.__matmul__(weights1)` → `matmul(data, weights1)`
  - Line 542: `train_data.__matmul__(w1)` → `matmul(train_data, w1)`

**Files intentionally left unchanged**:

- `shared/core/extensor.mojo` — contains `fn __matmul__` definition (operator implementation)
- `examples/mojo-patterns/trait_example.mojo` — contains `fn __matmul__` trait definition
- `tests/shared/core/test_matrix.mojo` — uses `a @ b` operator form and only references `__matmul__` in docstrings

**Key insight**: In this codebase, `matmul` was already imported in every function where `__matmul__` was called directly — no import changes were needed.
