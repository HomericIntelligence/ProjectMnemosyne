---
name: nd-tensor-dataloader-fix
description: 'Fix DataLoader.next() to support N-D tensors by replacing hardcoded
  2D shape assumption with ExTensor.slice(). Use when: DataLoader produces wrong batch
  shapes for 3D/4D data, or adding N-D batch slicing tests in Mojo.'
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Attribute | Value |
|-----------|-------|
| **Skill Name** | nd-tensor-dataloader-fix |
| **Category** | testing |
| **Language** | Mojo |
| **Issue Type** | DataLoader N-D tensor shape bug |
| **Resolution** | Replace manual shape construction with `ExTensor.slice()` |

## When to Use

- `DataLoader.next()` crashes with an index-out-of-range on tensors with fewer or more than 2 dimensions
- Batch slices of image data `(N, C, H, W)` collapse to wrong shape (e.g., `(batch, width)` instead of `(batch, C, H, W)`)
- Adding tests for 3D, 4D, or N-D batch extraction from a `DataLoader`
- Labels slicing also returns a wrong shape when labels are multi-dimensional

## Verified Workflow

### Step 1: Identify the hardcoded 2D assumption

In `shared/training/trainer_interface.mojo`, `DataLoader.next()` contained:

```mojo
var batch_data_shape = List[Int]()
batch_data_shape.append(actual_batch_size)
batch_data_shape.append(self.data.shape()[1])   # ← 2D-only, crashes for 1D or 4D
var batch_data = ExTensor(batch_data_shape, self.data.dtype())
```

This allocates a *new* zero tensor with only 2 dimensions, ignoring channels and spatial dims.

### Step 2: Replace with ExTensor.slice()

`ExTensor.slice(start, end, axis=0)` already returns a view preserving all trailing dimensions:

```mojo
# Extract batch slice — supports N-D tensors (2D, 3D, 4D, etc.)
var batch_data = self.data.slice(start_idx, end_idx)
var batch_labels = self.labels.slice(start_idx, end_idx)
```

No shape list needed. The returned tensor has shape `(end-start, d1, d2, ...)` for any N-D input.

### Step 3: Add N-D tests to the test file

Import `DataLoader` directly from the submodule (not from `shared.training` parent — Mojo re-export limitation):

```mojo
from shared.training.trainer_interface import DataLoader
```

Test pattern for 4D (image) data:

```mojo
fn test_dataloader_4d_batch_slicing() raises:
    var data = ones([8, 2, 4, 4], DType.float32)
    var labels = zeros([8], DType.float32)
    var loader = DataLoader(data^, labels^, 4)

    var batch = loader.next()
    assert_equal(batch.data.shape()[0], 4)
    assert_equal(batch.data.shape()[1], 2)
    assert_equal(batch.data.shape()[2], 4)
    assert_equal(batch.data.shape()[3], 4)
```

Test all batches preserve trailing dims (including partial last batch):

```mojo
fn test_dataloader_nd_shape_preserved() raises:
    var data = ones([9, 3, 8, 8], DType.float32)
    var labels = zeros([9], DType.float32)
    var loader = DataLoader(data^, labels^, 4)

    while loader.has_next():
        var batch = loader.next()
        assert_equal(batch.data.shape()[1], 3)
        assert_equal(batch.data.shape()[2], 8)
        assert_equal(batch.data.shape()[3], 8)
```

### Step 4: Handle GLIBC mismatch on local host

If `mojo test` fails with `GLIBC_2.32/2.33/2.34 not found`, the local host has too old a libc.
Pre-commit hooks include `mojo format` which also fails. Use `SKIP=mojo-format` only when
the host cannot run the mojo binary, and let CI validate format in Docker:

```bash
# All pre-commit hooks pass when mojo binary IS available
git add <files> && git commit -m "fix(...): ..."
# If GLIBC blocks mojo format:
SKIP=mojo-format git commit -m "fix(...): ..."
```

In this session, `mojo format` ran successfully (pre-commit passed clean), so no skip was needed.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running tests locally | `pixi run mojo test tests/shared/training/test_training_loop.mojo` | GLIBC_2.32/2.33/2.34 not found on host | Local host GLIBC too old; Mojo tests must run in Docker/CI |
| Manual shape construction | Considered building `batch_data_shape` with a loop over `self.data.shape()` | More complex than needed, would still allocate new tensor | `ExTensor.slice()` is already implemented and returns a shared-memory view |

## Results & Parameters

### Minimal fix (2 lines changed)

```mojo
# Before (2D-only):
var batch_data_shape = List[Int]()
batch_data_shape.append(actual_batch_size)
batch_data_shape.append(self.data.shape()[1])
var batch_data = ExTensor(batch_data_shape, self.data.dtype())

var batch_labels_shape = List[Int]()
batch_labels_shape.append(actual_batch_size)
var batch_labels = ExTensor(batch_labels_shape, self.labels.dtype())

# After (N-D):
var batch_data = self.data.slice(start_idx, end_idx)
var batch_labels = self.labels.slice(start_idx, end_idx)
```

### Mojo submodule import pattern

```mojo
# Use direct submodule import — Mojo re-export limitations prevent using parent package
from shared.training.trainer_interface import DataLoader
# NOT: from shared.training import DataLoader  (may fail)
```

### ExTensor.slice() signature

```mojo
fn slice(self, start: Int, end: Int, axis: Int = 0) raises -> ExTensor
# Returns a shared-memory view. Modifying the slice modifies the original.
# Shape of result: (end-start, d1, d2, ...) for any number of trailing dims.
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #3846, Issue #3277 | [notes.md](../references/notes.md) |
