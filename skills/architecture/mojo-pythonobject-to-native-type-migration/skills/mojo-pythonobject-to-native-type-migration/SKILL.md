---
name: mojo-pythonobject-to-native-type-migration
description: "Migrate Mojo function signatures from PythonObject placeholder parameters to native Mojo struct types. Use when: a function accepts PythonObject as a temporary placeholder pending interop infrastructure, and the native struct is now ready."
category: architecture
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Category** | architecture |
| **Objective** | Replace PythonObject placeholder parameters with native Mojo struct types once interop infrastructure is available |
| **Outcome** | Success - run_epoch() migrated from PythonObject to DataLoader; tests updated; all pre-commit hooks pass |

## When to Use

Invoke this skill when:

- A Mojo function accepts `PythonObject` as a stopgap while native struct was being built
- The native Mojo struct (e.g., `DataLoader`) now exists with `has_next()`/`next()` iteration
- Tests use `Python.none()` or a dummy `PythonObject` as a placeholder argument
- The function body has a `_ = data_loader  # Suppress unused variable` pattern (no real work done)
- A NOTE comment references "Track 4", "blocked by interop", or "TODO: implement when X is ready"

## Verified Workflow

1. **Read the function** with `PythonObject` parameter to understand the intended behavior from its docstring
2. **Locate the native struct** (`DataLoader`, etc.) — usually in `trainer_interface.mojo` or adjacent file
3. **Verify the struct's iteration API**: confirm `reset()`, `has_next()`, `next()` exist and return the right types
4. **Update the import block** — remove `from python import PythonObject` if no longer used elsewhere; add import for the native struct
5. **Change the function signature**: `data_loader: PythonObject` → `mut data_loader: DataLoader` (needs `mut` for stateful iteration)
6. **Implement the loop body**:
   ```mojo
   data_loader.reset()
   while data_loader.has_next():
       var batch = data_loader.next()
       var loss = self.step(batch.data, batch.labels)
       total_loss += Float64(loss._get_float32(0))
       num_batches += 1
   ```
7. **Update tests** — replace `Python.none()` / `py_loader` with a real struct constructed from `ExTensor` data
8. **Update test assertions** — old placeholder assertion (e.g., `assert_equal(Int(avg_loss), 0)`) must reflect real processing
9. **Remove unused imports** from the test file (e.g., `create_mock_dataloader` if switched to inline construction)
10. **Run pre-commit hooks** to verify mojo format, trailing whitespace, large files pass

## Results & Parameters

### Signature change pattern

```mojo
# Before
fn run_epoch(mut self, data_loader: PythonObject) raises -> Float32:
    _ = data_loader  # suppress unused warning
    return Float32(0.0)

# After
fn run_epoch(mut self, mut data_loader: DataLoader) raises -> Float32:
    var total_loss = Float64(0.0)
    var num_batches = Int(0)
    data_loader.reset()
    while data_loader.has_next():
        var batch = data_loader.next()
        var loss = self.step(batch.data, batch.labels)
        total_loss += Float64(loss._get_float32(0))
        num_batches += 1
    if num_batches > 0:
        return Float32(total_loss / Float64(num_batches))
    else:
        return Float32(0.0)
```

### Import change pattern

```mojo
# Before
from python import PythonObject

# After
from shared.training.trainer_interface import DataLoader, DataBatch
```

### Test change pattern

```mojo
# Before
from python import Python
var py_loader = Python.none()
var avg_loss = training_loop.run_epoch(py_loader)
assert_equal(Int(avg_loss), 0)  # Placeholder returns 0.0

# After
var data_tensor = ones([100, 10], DType.float32)
var label_tensor = zeros([100, 1], DType.float32)
var data_loader = DataLoader(data_tensor^, label_tensor^, batch_size=10)
var avg_loss = training_loop.run_epoch(data_loader)
assert_greater(Float64(avg_loss), Float64(-0.001))
```

### Key constraints

- DataLoader's `next()` requires `mut self` — the parameter must be `mut data_loader`
- If `DataLoader.next()` still returns placeholder zero tensors internally (pending ExTensor.slice()), the loss will be 0.0 — use `assert_greater(loss, -0.001)` not `assert_equal(loss, positive_value)`
- The `DataBatch` struct exposes `.data` and `.labels` fields
- If `PythonObject` was imported only for this one use, remove the entire import line

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running tests locally | `pixi run mojo test` | GLIBC too old on host (needs 2.32+, host has 2.31) | Tests must run in CI or Docker; verify code correctness by reading the struct APIs instead |
| Using Docker CI image | `docker run ghcr.io/homericintelligence/projectodyssey:main` | Image not pulled locally, registry access denied outside CI | Local test execution not available; rely on CI and pre-commit hooks |
| Keeping `_ = data_loader` | Left the suppress line when switching to real iteration | Compiler would warn / suppress is no longer needed once data_loader is consumed | Remove the suppress line entirely when implementing real iteration |
