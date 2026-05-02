---
name: mojo-dual-type-tensor-review
description: "Documents the dual-type tensor architecture (Tensor[dtype] + AnyTensor) for Mojo ML frameworks, including feasibility review and corner cases. Use when: (1) designing typed vs type-erased tensor APIs in Mojo, (2) reviewing parametric struct migration plans for completeness, (3) understanding Mojo 0.26.1 parametric limitations."
category: architecture
date: 2026-03-21
version: "1.0.0"
user-invocable: false
---

# Mojo Dual-Type Tensor Architecture Review

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-21 |
| **Objective** | Design and review a dual-type tensor system for Mojo ML: Tensor[dtype] (compile-time typed) + AnyTensor (runtime typed) |
| **Outcome** | Architecture validated with 2 blockers, 6 high issues found and documented |
| **Mojo Version** | 0.26.1 |
| **Epic** | ProjectOdyssey #4998 |

## When to Use

- Designing typed vs type-erased container APIs in Mojo
- Planning parametric struct migrations for large codebases
- Reviewing migration plans for completeness before implementation
- Understanding Mojo 0.26.1 parametric type limitations
- Auditing codebases for dtype safety (missing guards)

## Verified Workflow

### Quick Reference

```text
Architecture:
  Tensor[dtype: DType]  -- compile-time typed, SIMD-like assignment
  AnyTensor             -- runtime typed, for collections/IO/traits
  TensorLike            -- shared trait interface

Naming convention follows Mojo stdlib: AnyType, AnyOrigin -> AnyTensor

Key constraint: auto-parameterization does NOT work for return types
  FAILS:  fn relu(t: Tensor) -> Tensor
  WORKS:  fn relu[dt: DType](t: Tensor[dt]) -> Tensor[dt]
  Call sites still infer dt: relu(my_tensor) works without [DType.float32]
```

### Step 1: Audit the Codebase Quantitatively

Before designing, count everything:
- Functions taking/returning the tensor type (368 takes, 480 returns for ExTensor)
- Runtime dtype branch checks (351 total)
- Bitcast pointer accesses (708 total)
- Heterogeneous collections (List, Dict usage)
- Struct fields storing the tensor type
- Trait signatures referencing the tensor type

### Step 2: Test Mojo Parametric Capabilities

Write and compile small test programs to verify:
- Parametric struct conforming to trait: YES
- `comptime Alias = OriginalType` for backward compat: YES
- Auto-parameterization for return types: NO (BLOCKER)
- `List[TraitName]` trait objects: NO (Mojo has no existentials)
- `Variant[TypeA, TypeB]` tagged union: YES
- Multi-param structs `Batch[data_dt, label_dt]`: YES
- Zero-copy bitcast views (ASAP destruction safe): YES
- Default parameter values: YES
- Chained auto-param function calls: requires explicit `[dt: DType]`

### Step 3: Identify Corner Cases

Search the codebase for patterns that break under parametric types:
- Heterogeneous collections (model params, state dicts, dataset batches)
- Runtime dtype from file I/O, CLI config
- Cross-dtype operations (mixed precision)
- Struct fields with different dtypes (Batch: float data + int labels)
- Trait method signatures
- Pointer arithmetic with `* dtype_size` (must be removed for typed pointers)
- Serialization (type parameter doesn't survive I/O)
- Lazy evaluation with `List[ExTensor]` fields

### Step 4: Assess Performance Impact

- Mojo uses eager instantiation (like C++ templates)
- N functions x M dtypes = N*M compiled bodies
- 317 functions x 11 dtypes = 3,487 worst-case instantiations
- Mitigation: restrict to 3 float types initially (float16/32/64)
- Memory pool is byte-level, dtype-agnostic -- no impact

### Step 5: Document Findings with Severity Levels

Categorize as BLOCKER / HIGH / MEDIUM / LOW with specific file:line references and concrete fixes.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Pure parametric ExTensor | Make ExTensor[dtype] the only type | Heterogeneous collections (List[ExTensor], Dict, Batch) break with no trait objects | Mojo 0.26.1 has no existential types; need a type-erased companion |
| Auto-parameterization for all functions | Rely on `fn relu(t: Tensor) -> Tensor` auto-inference | Return type auto-param fails: "failed to infer parameter dtype" | Must use explicit `[dt: DType]` on every function returning a parametric type |
| Change __getitem__ to return Float64 | Wider return type to accept more assignments | Float32 can't implicitly convert to Float64 in Mojo; broke 108 call sites | Mojo has zero implicit numeric conversions between float types |
| Proxy/reference return type from __getitem__ | Return a mutable proxy that accepts any assignment | "expression must be mutable in assignment" -- Mojo ownership prevents mutable references from __getitem__ | Mojo's ownership model doesn't support reference-returning subscript |
| Single-pass sub-agent migration | Launch 8 agents to fix all files at once | Agents only fixed 60% of errors; missed Float16 paths, arithmetic mismatches, parallelize closures | Sub-agents need explicit error categories and line numbers; plan for 2-3 rounds |

## Results & Parameters

### Dual-Type Architecture

```mojo
trait TensorLike(Copyable, Movable):
    fn numel(self) -> Int
    fn shape(self) -> List[Int]
    fn dtype(self) -> DType

struct Tensor[dtype: DType = DType.float32](TensorLike):
    var _data: UnsafePointer[Scalar[Self.dtype], origin=MutAnyOrigin]
    fn __getitem__(self, i: Int) raises -> Scalar[Self.dtype]: ...
    fn as_any(self) -> AnyTensor: ...
    fn cast[target: DType](self) raises -> Tensor[target]: ...

struct AnyTensor(TensorLike):
    var _data: UnsafePointer[UInt8, origin=MutAnyOrigin]
    var _dtype: DType
    fn as_tensor[dtype: DType](self) raises -> Tensor[dtype]: ...
    fn set(mut self, index: Int, value: Float64) raises: ...
```

### Review Findings Summary

```text
BLOCKERS (2):
  - Auto-param doesn't work for return types (must use explicit [dt: DType])
  - lazy_expression.mojo / lazy_eval.mojo missing from migration phases

HIGH (6):
  - Slice pointer arithmetic double-offset (remove * dtype_size for typed ptr)
  - I/O boundary underspecified (save via as_any(), load returns AnyTensor)
  - Phase 3->5 circular dependency (concatenate/stack/split use List[ExTensor])
  - __str__/__repr__ use _get_float64 (need typed access)
  - Scope underestimated 30-50% (explicit [dt: DType] on 480 signatures)
  - Binary bloat risk (eager instantiation, 317 fns x 11 dtypes)

MEDIUM (5):
  - In-place operator precision bug (pre-existing)
  - __hash__ precision loss for int types
  - Hashable not specified in TensorLike trait
  - SIMD helpers should merge to single parametric version
  - Circular import in tensor_io.mojo

Bugs found during audit (fixed in PR #5001):
  - conv2d: no dtype guard on kernel/bias vs input
  - batch_norm2d: no dtype guard on gamma/beta/running_stats vs input
  - attention: no dtype guard on mask vs scores
```

### Mojo 0.26.1 Documentation References

```text
Parameters:     github.com/modular/modular/blob/modular/v26.1/mojo/docs/manual/parameters/index.mdx
Traits:         github.com/modular/modular/blob/modular/v26.1/mojo/docs/manual/traits.mdx
Types (SIMD):   github.com/modular/modular/blob/modular/v26.1/mojo/docs/manual/types.mdx
UnsafePointer:  github.com/modular/modular/blob/modular/v26.1/mojo/docs/manual/pointers/unsafe-pointers.mdx
Lifecycle:      github.com/modular/modular/blob/modular/v26.1/mojo/docs/manual/lifecycle/life.mdx
```
