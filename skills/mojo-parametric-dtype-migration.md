---
name: mojo-parametric-dtype-migration
description: "Pattern for migrating a Mojo runtime-typed struct to a parametric compile-time typed struct with backward-compat alias and parallel sub-agent workflow. Use when: (1) splitting a runtime-typed Mojo struct into parametric + type-erased pair, (2) orchestrating large-scale codebase renames with parallel agents in worktrees, (3) resolving circular imports between parametric and type-erased Mojo types."
category: architecture
date: 2026-03-22
version: 1.0.0
user-invocable: false
tags:
  - mojo
  - parametric
  - refactoring
  - parallel-agents
  - worktrees
---

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-22 |
| **Objective** | Migrate ExTensor (runtime-typed, UnsafePointer[UInt8]) to Tensor[dtype: DType] (compile-time typed, UnsafePointer[Scalar[dtype]]) + AnyTensor (renamed ExTensor) across 600+ files / ~15,700 lines |
| **Outcome** | 6 integrated PRs merged via 22+ sub-agent invocations with parallel worktrees |
| **Epic** | HomericIntelligence/ProjectOdyssey#4998 |
| **PRs** | #5002, #5006, #5010, #5015, #5019, #5023 |

## When to Use

1. Splitting a runtime-typed Mojo struct into a parametric (compile-time typed) version + type-erased wrapper
2. Orchestrating a large-scale codebase migration (500+ files) using parallel sub-agents in git worktrees
3. Resolving circular imports between a new parametric type and the original type-erased type in Mojo
4. Designing zero-copy conversion between parametric and type-erased Mojo structs with shared refcount
5. Handling Mojo v0.26.1 limitations: no parametric trait methods, no variadic generics, re-export chain issues

## Verified Workflow

### Quick Reference

```text
Phase dependency graph:
  ADR → Tensor[dtype]+AnyTensor → Factories+Ops → Layers+Traits → Collections+Training → Cleanup

Per-phase 4-stage agent pattern:
  1. Implementation agent (worktree) — source code only
  2. Testing agent (worktree) — TDD tests only, in parallel with #1
  3. Review agent — reviews both outputs
  4. Fix/integration agent (worktree) — addresses findings, creates PR

Integration branch pattern:
  main ← integration-branch ← sub-PR-1, sub-PR-2, sub-PR-3 (merge into integration, then PR to main)
```

### Step 1: Create ADR documenting the dual-type architecture

Before any code, document the decision: parametric type + type-erased wrapper + shared trait. Include all review findings (blockers, high, medium, low) from the design review.

### Step 2: Create the parametric struct (additive, non-breaking)

Create the new `Tensor[dtype: DType]` struct in a new package (`shared/tensor/`). Key design:

```mojo
struct Tensor[dtype: DType = DType.float32](TensorLike):
    var _data: UnsafePointer[Scalar[Self.dtype]]  # Typed pointer, NOT UInt8
    var _shape: List[Int]
    var _strides: List[Int]
    var _numel: Int
    var _is_view: Bool
    var _refcount: UnsafePointer[Int]
    # NO _dtype field — it's Self.dtype (compile-time parameter)

    fn __getitem__(self, index: Int) raises -> Scalar[Self.dtype]:
        return self._data[index]  # Zero-branch typed access
```

Internal constructor for zero-copy conversion (B4 — shared refcount):

```mojo
fn __init__(out self, data: UnsafePointer[Scalar[dtype]], shape: List[Int],
            strides: List[Int], refcount: UnsafePointer[Int], ...):
    self._refcount = refcount
    self._refcount[] += 1  # CRITICAL: shared ownership
```

### Step 3: Rename the original struct with backward-compat alias

```mojo
# In extensor.mojo:
struct AnyTensor(TensorLike):  # was ExTensor
    ...

comptime ExTensor = AnyTensor  # Backward compat — ALL existing code compiles
```

Remove naming collision: `comptime Tensor = ExTensor` from `shared/__init__.mojo`.

### Step 4: Resolve circular import for as_tensor()

`extensor.mojo` can't import `Tensor` at module level (tensor.mojo already imports ExTensor). Use function-scoped local import:

```mojo
fn as_tensor[dtype: DType](self) raises -> Tensor[dtype]:
    from shared.tensor.tensor import Tensor  # Local import breaks cycle
    return Tensor[dtype](self._data.bitcast[Scalar[dtype]](), ...)
```

### Step 5: Add typed overloads using wrapping pattern

For each existing function, add a typed overload alongside (don't remove originals):

```mojo
fn relu[dt: DType](input: Tensor[dt]) raises -> Tensor[dt]:
    return relu(input.as_any()).as_tensor[dt]()
```

All 480 functions need explicit `[dt: DType]` — auto-parameterization does NOT work for return types (B1).

### Step 6: Update traits to AnyTensor (Module boundary stays AnyTensor)

```mojo
trait Module:
    fn forward(mut self, input: AnyTensor) raises -> AnyTensor  # Can't be parametric in Mojo 0.26.1
```

Layers convert at boundaries: `input.as_tensor[dtype]()` → compute → `result.as_any()`

### Step 7: Mechanical rename across all test and example files

Use parallel sub-agents to process test directories simultaneously. The `comptime ExTensor = AnyTensor` alias keeps everything compiling until the final cleanup phase.

### Step 8: Final cleanup — remove alias, rename file

```bash
# Remove alias
# Rename: extensor.mojo → any_tensor.mojo
# Update ALL import paths
# Verify: grep -rn "ExTensor" shared/ tests/ returns ZERO results
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Package split (Phase 0) | Move files to `shared/base/`, `shared/tensor/`, `shared/core/` physically | 500+ import path changes with zero functional value; Mojo re-export chain limitation (#3754) prevents transparent backward compat | Keep files in place, create new package only for genuinely new files |
| Auto-parameterized return types | `fn relu(t: Tensor) -> Tensor` without explicit `[dt: DType]` | "failed to infer parameter 'dtype'" — Mojo can't infer return type params from input params | All 480 functions need explicit `[dt: DType]` parameter (B1) |
| Monolithic sub-agent for keystone PR | Single agent implementing Tensor[dtype] + AnyTensor rename + tests in one worktree | Too large for one agent, hard to parallelize, no separation of concerns | Split into impl/test/review/fix agents in separate worktrees |
| Parameter rename `dtype` → `dt` on struct | Three agents independently renamed struct parameter to avoid perceived method-param collision | `struct Tensor[dtype: DType]` + `fn dtype() -> DType` already compiles in Mojo v0.26.1 — the collision doesn't exist | Test the actual compiler behavior before "fixing" assumed issues |
| `as_any()` heap surgery | Create ExTensor, free its allocation, replace fields with shared data pointer | Fragile, potential double-free, violates B4 refcount protocol | Use internal constructor that takes all fields + shared refcount pointer |
| `bitcast[Float32]()` in parameterized layers | Copy layer parameters via `bitcast[Float32]()` regardless of dtype parameter | Silent data corruption for float64/float16 tensors — bitcast reinterprets bytes | Use typed `Tensor[dtype]._data` directly, no bitcast needed |
| B4 refcount test in same scope | Create source + converted tensor in same scope, assert data valid | Mojo ASAP destruction doesn't fire within same scope — test always passes even with broken refcount | Use helper functions that force source out of scope before assertion |
| Module-level import for circular types | `from shared.tensor.tensor import Tensor` at top of `extensor.mojo` | Circular: `extensor` ↔ `tensor` | Function-scoped `from shared.tensor.tensor import Tensor` inside method body |
| Renaming `TensorLike.dtype()` → `get_dtype()` | Avoid perceived param-method collision | Breaks 50+ existing call sites of `.dtype()` across codebase; collision doesn't exist | Don't rename working APIs based on assumptions |

## Results & Parameters

### Workflow Configuration

```yaml
# Integration branch pattern
integration_branch: "4998-pr3-5-core-ops"  # Shared target for sub-PRs
sub_pr_base: integration_branch  # Sub-PRs target integration, NOT main
final_pr_base: main  # Integration branch → main

# 4-stage agent pattern per PR
stage_1: implementation_agent (worktree isolation)
stage_2: testing_agent (worktree isolation, parallel with stage_1)
stage_3: review_agent (no worktree, reads both outputs)
stage_4: fix_integration_agent (worktree, combines + creates sub-PR)

# Parallelization strategy
parallel_safe:
  - Different source files (shape.mojo vs elementwise.mojo)
  - New files vs existing file modifications
  - Different test directories
not_parallel_safe:
  - Same file modifications (extensor.mojo rename + as_tensor method)
  - Trait changes before trait-implementing layers
```

### Critical Design Constraints

```yaml
# B4: Zero-copy conversion refcount protocol
as_tensor_protocol:
  - Share _refcount pointer (NOT allocate new)
  - Increment refcount in constructor
  - Both Tensor.__del__ and AnyTensor.__del__ decrement
  - Test with helper function forcing source out of scope

# H1: Typed pointer arithmetic
typed_pointer_rule: "UnsafePointer[Scalar[dtype]] auto-scales — do NOT multiply by dtype_size"

# H7: Module boundary
module_boundary: "forward(AnyTensor) -> AnyTensor — can't be parametric in Mojo 0.26.1"
layer_pattern: "input.as_tensor[dtype]() → compute → result.as_any()"

# Circular import resolution
circular_import_fix: "Function-scoped local import inside method body"
```

### Migration Statistics

```text
Total PRs: 6 integrated (from 22+ sub-agent invocations)
Total files: 600+ modified
Total lines: ~15,700 changed
Sub-agents: 22+ launched across implementation, testing, review, fix roles
Critical bugs caught by review: 3 (bitcast corruption, byte-index copy, ASAP test inadequacy)
Phases: 11 (ADR → Tensor[dtype] → Factories → Ops → Layers → Traits → Collections → Training → Core tests → Other tests → Cleanup)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Epic #4998, PRs #5002-#5023 | Full ExTensor → Tensor[dtype] + AnyTensor migration |
