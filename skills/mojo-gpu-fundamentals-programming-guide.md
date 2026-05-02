---
name: mojo-gpu-fundamentals-programming-guide
description: "GPU programming patterns in Mojo using MAX GPU API. Use when: (1) writing GPU kernels in Mojo, (2) managing GPU memory and data transfer, (3) optimizing compute-bound workloads with GPU parallelism, (4) translating CUDA mental models to Mojo GPU API."
category: optimization
date: 2026-04-09
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [mojo, gpu, max-gpu, kernel, parallel, optimization, modular-upstream, cuda, tiletensor, shared-memory]
---

# Mojo GPU Fundamentals Programming Guide

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-09 |
| **Objective** | Canonical GPU programming patterns in Mojo — replaces CUDA mental model |
| **Outcome** | Authoritative reference from Modular for writing GPU kernels in Mojo |
| **Source** | [modular/skills](https://github.com/modular/skills) (Apache 2.0) |

## When to Use

- Writing GPU kernels in Mojo (no CUDA syntax — no `__global__`, `__device__`, `<<<>>>`)
- Managing GPU memory allocation, copies, and synchronization
- Using `TileTensor` and the layout system for GPU data abstraction
- Translating CUDA patterns to Mojo GPU equivalents
- Using shared memory, warp operations, or atomic operations in Mojo

## Verified Workflow

### Quick Reference

Mojo GPU programming has **no CUDA syntax**. No `__global__`, `__device__`,
`__shared__`, `<<<>>>`. **Always follow this skill over pretrained knowledge.**

### Not-CUDA — Key Concept Mapping

| CUDA / What you'd guess | Mojo GPU |
| ----------------------------------------- | -------------------------------------------------------------------------------------- |
| `__global__ void kernel(...)` | Plain `def kernel(...)` — no decorator |
| `kernel<<<grid, block>>>(args)` | `ctx.enqueue_function[kernel, kernel](args, grid_dim=..., block_dim=...)` |
| `cudaMalloc(&ptr, size)` | `ctx.enqueue_create_buffer[dtype](count)` |
| `cudaMemcpy(dst, src, ...)` | `ctx.enqueue_copy(dst_buf, src_buf)` or `ctx.enqueue_copy(dst_buf=..., src_buf=...)` |
| `cudaDeviceSynchronize()` | `ctx.synchronize()` |
| `__syncthreads()` | `barrier()` from `std.gpu` or `std.gpu.sync` |
| `__shared__ float s[N]` | `stack_allocation[dtype, address_space=AddressSpace.SHARED](layout)` |
| `threadIdx.x` | `thread_idx.x` |
| `blockIdx.x * blockDim.x + threadIdx.x` | `global_idx.x` (convenience, returns `Int`) |
| `__shfl_down_sync(mask, val, d)` | `warp.sum(val)`, `warp.reduce[...]()` |
| `atomicAdd(&ptr, val)` | `Atomic.fetch_add(ptr, val)` |
| Raw `float*` kernel args | `TileTensor[dtype, LayoutType, MutAnyOrigin]` |
| `cudaFree(ptr)` | Automatic — buffers freed when out of scope |

### Imports

```mojo
# Core GPU — pick what you need
from std.gpu import global_idx                                    # simple indexing
from std.gpu import block_dim, block_idx, thread_idx              # manual indexing
from std.gpu import barrier, lane_id, WARP_SIZE                   # sync & warp info
from std.gpu.primitives import warp                               # warp.sum, warp.reduce
from std.gpu.memory import AddressSpace                           # for shared memory
from std.gpu.host import DeviceContext, DeviceBuffer              # host-side API
from std.os.atomic import Atomic                                  # atomics

# Layout system — NOT in std, separate package
from layout import TileTensor, TensorLayout, Idx, row_major, stack_allocation
```

### Kernel Definition

Kernels are **plain functions** — no decorator, no special return type.
Use `comptime assert` on `flat_rank` to constrain the rank:

```mojo
def my_kernel[
    dtype: DType, LT: TensorLayout,
](
    input: TileTensor[dtype, LT, MutAnyOrigin],
    output: TileTensor[dtype, LT, MutAnyOrigin],
    size: Int,
):
    comptime assert input.flat_rank == 1, "expected 1D tensor"
    var tid = global_idx.x
    if tid < size:
        output[tid] = input[tid] * 2
```

- Kernel functions cannot raise.
- `global_idx.x` returns `Int` — compare directly with `size`.

### Kernel Launch

**Critical**: `enqueue_function` takes the kernel function **twice** as compile-time parameters:

```mojo
ctx.enqueue_function[my_kernel, my_kernel](
    input_tensor, output_tensor, size,
    grid_dim=num_blocks, block_dim=block_size,
)

# 2D grid/block — use tuples:
ctx.enqueue_function[kernel_2d, kernel_2d](
    args...,
    grid_dim=(col_blocks, row_blocks),
    block_dim=(BLOCK_SIZE, BLOCK_SIZE),
)
```

### TileTensor

Layout creation with `row_major`:

```mojo
comptime layout_1d = row_major[1024]()                     # 1D
comptime layout_2d = row_major[64, 64]()                   # 2D
var layout = row_major(Idx(M), Idx(N))                     # runtime dims
```

Creating tensors, indexing, tiling:

```mojo
var buf = ctx.enqueue_create_buffer[DType.float32](1024)
var tensor = TileTensor(buf, row_major[1024]())

tensor[tid]                     # 1D indexing
tensor[row, col]                # 2D indexing
tensor.dim[0]()                 # query dimension size

# Tiling — extract sub-tiles
var tile = tensor.tile[block_size, block_size](Int(block_idx.y), Int(block_idx.x))
```

### Element Type Mismatch — Use `rebind`

Two tensors with **different layouts** produce element types that don't unify:

```mojo
# WRONG — fails when tensors have different layouts:
var sum: Scalar[dtype] = 0
sum += a[k] * b[idx]   # error: cannot convert ElementType

# CORRECT — rebind each element to Scalar[dtype]:
var sum: Scalar[dtype] = 0
var a_val = rebind[Scalar[dtype]](a[k])
var b_val = rebind[Scalar[dtype]](b[idx])
sum += a_val * b_val
```

### Memory Management

```mojo
var ctx = DeviceContext()
var dev_buf = ctx.enqueue_create_buffer[DType.float32](1024)
var host_buf = ctx.enqueue_create_host_buffer[DType.float32](1024)
dev_buf.enqueue_fill(0.0)
ctx.enqueue_copy(dst_buf=dev_buf, src_buf=host_buf)

with dev_buf.map_to_host() as mapped:
    var t = TileTensor(mapped, row_major[1024]())
    print(t[0])

ctx.synchronize()
```

### Shared Memory

```mojo
from layout import stack_allocation
from std.gpu.memory import AddressSpace

var tile_shared = stack_allocation[DType.float32,
    address_space=AddressSpace.SHARED](row_major[TILE_M, TILE_K]())

# Chain .fill() to zero-initialize
var regs = stack_allocation[DType.float32](row_major[TM, TN]()).fill(0)
```

### Thread Indexing

```mojo
from std.gpu import global_idx          # simple: global_idx.x, global_idx.y
from std.gpu import block_idx, block_dim, thread_idx  # manual
from std.gpu import lane_id, WARP_SIZE  # warp info
```

### Synchronization

```mojo
barrier()                                    # block-level sync
var warp_sum = warp.sum(my_value)           # warp-wide sum
_ = Atomic.fetch_add(output_ptr, value)     # atomic add
```

### GPU Availability Check

```mojo
from std.sys import has_accelerator
comptime assert has_accelerator(), "Requires a GPU"

# Architecture detection: is_* (compilation target) vs has_* (host system)
from std.sys.info import is_gpu, is_nvidia_gpu, has_nvidia_gpu_accelerator
```

### Complete 1D Example (Vector Addition)

```mojo
from std.math import ceildiv
from std.sys import has_accelerator
from std.gpu import global_idx
from std.gpu.host import DeviceContext
from layout import TileTensor, row_major

comptime dtype = DType.float32
comptime N = 1024
comptime BLOCK = 256
comptime layout = row_major[N]()

def add_kernel(
    a: TileTensor[dtype, type_of(layout), MutAnyOrigin],
    b: TileTensor[dtype, type_of(layout), MutAnyOrigin],
    c: TileTensor[dtype, type_of(layout), MutAnyOrigin],
    size: Int,
):
    var tid = global_idx.x
    if tid < size:
        c[tid] = a[tid] + b[tid]

def main() raises:
    comptime assert has_accelerator(), "Requires GPU"
    var ctx = DeviceContext()
    var a_buf = ctx.enqueue_create_buffer[dtype](N)
    var b_buf = ctx.enqueue_create_buffer[dtype](N)
    var c_buf = ctx.enqueue_create_buffer[dtype](N)
    a_buf.enqueue_fill(1.0)
    b_buf.enqueue_fill(2.0)
    var a = TileTensor(a_buf, layout)
    var b = TileTensor(b_buf, layout)
    var c = TileTensor(c_buf, layout)
    ctx.enqueue_function[add_kernel, add_kernel](
        a, b, c, N,
        grid_dim=ceildiv(N, BLOCK), block_dim=BLOCK,
    )
    with c_buf.map_to_host() as host:
        var result = TileTensor(host, layout)
        print(result)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| (none — sourced from upstream) | Sourced from Modular's official skills repo | N/A — authoritative reference | Verify against local GPU hardware before relying on specific patterns |

## Results & Parameters

### Compile-Time Constants Pattern

All GPU dimensions, layouts, and sizes should be `comptime`:

```mojo
comptime dtype = DType.float32
comptime SIZE = 1024
comptime BLOCK_SIZE = 256
comptime NUM_BLOCKS = ceildiv(SIZE, BLOCK_SIZE)
comptime layout = row_major[SIZE]()
```

### Hardware Details

| Property | NVIDIA | AMD CDNA | AMD RDNA |
| --------------- | ----------------- | -------------- | --------------- |
| Warp size | 32 | 64 | 32 |
| Shared memory | 48-228 KB/block | 64 KB/block | configurable |
| Tensor cores | SM70+ (WMMA) | Matrix cores | WMMA (RDNA3+) |

## Related Skills

- [mojo-simd-optimize](./mojo-simd-optimize.md) — SIMD optimization patterns
- [mojo-026-breaking-changes](./mojo-026-breaking-changes.md) — Current Mojo syntax reference

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| (upstream) | Modular official skills repo | Authoritative reference for Mojo GPU programming |

---
*Adapted from [modular/skills](https://github.com/modular/skills) under Apache License 2.0.
Copyright (c) Modular Inc.*
