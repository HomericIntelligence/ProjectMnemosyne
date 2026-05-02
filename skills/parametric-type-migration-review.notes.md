# Parametric Type Migration Review - Detailed Notes

## Session Context

**Date**: 2026-03-21
**Epic**: https://github.com/HomericIntelligence/ProjectOdyssey/issues/4998
**Plan Document**: ~/ExTensorRefactor.md (1,195 lines)

## Objective

Review the ExTensor → Tensor[dtype] + AnyTensor migration plan for completeness, find gaps, integrate findings, update epic #4998, and generate implementation prompt with parallel sub-agent orchestration.

## Codebase Scale

- ExTensor struct: 4,703 lines in shared/core/extensor.mojo
- 569 files import ExTensor
- 395 test files reference ExTensor (4,793 total references)
- 480 functions return ExTensor, 368 take it as parameter
- 708 `_data.bitcast[T]()` calls across shared/
- 177 dtype branch checks inside extensor.mojo

## Key Discoveries

### New Blockers Found

**B3: comptime Tensor = ExTensor naming collision**
- Location: shared/__init__.mojo:82
- Also: 8 test files with local comptime Tensor = ExTensor aliases
- Fix: Remove alias BEFORE creating new struct Tensor[dtype]

**B4: Refcount protocol for zero-copy conversion**
- Location: extensor.mojo:435-489 (copyinit/del protocol)
- `as_tensor[dtype]()` and as_any() must share `_refcount` pointer and increment it
- Without this: ASAP destruction of source causes UAF on the view
- Required test: create source, convert, drop source, verify view data intact

### Critical Architecture Decisions

**3-layer package split** (user chose this over 2-layer):
- shared/base/: memory_pool, broadcasting, dtype_ordinal, constants (all verified zero ExTensor imports)
- shared/tensor/: Tensor[dtype], AnyTensor (renamed ExTensor), TensorLike trait, gradient_types, validation, tensor_io
- shared/core/: All 40+ operation files, traits, module, sequential, layers

**Dependency verification**:
- extensor.mojo only imports from: memory_pool, broadcasting, dtype_ordinal → all base layer
- broadcasting.mojo has ZERO imports from shared → pure stdlib functions
- validation.mojo imports extensor → stays in tensor layer
- traits.mojo imports extensor → stays in core layer (cross-layer import, acyclic)

**Module/Sequential limitation**:
- Only Linear and ReLULayer implement Module trait
- BatchNorm2dLayer, Conv2dLayer, DropoutLayer do NOT implement Module
- Module stays on AnyTensor permanently (Mojo 0.26.1 can't parameterize trait methods)
- Type safety applies only inside individual layer implementations

### Scope Revision

| Phase | Original | Revised | Why |
| ------- | ---------- | --------- | ----- |
| Phase 1 | ~200 changed | ~1,500 | Rename in 4,703-line file + alias + collision fix |
| Phase 7 | ~3,000 | ~5,600 | 3,975 creation calls + 412 imports, not 8 lines/file |
| Total | 9,700 | 15,700 | Across all phases |

### Language Feature Verification (Mojo 0.26.1)

| Feature | Existing Usage | Works? |
| --------- | --------------- | -------- |
| Auto-parameterization | 0 instances in codebase | Partially (fails for return types) |
| comptime aliases | 7+ instances | Yes |
| Variant | 0 instances | Yes (verified) |
| @parameter if | 0 instances | Yes (verified) |
| rebind | 0 instances | No (same-type assertion only) |
| Parametric structs | 4 (Sequential2-5) | Yes |
| [T: DType] function params | 63 functions | Yes |

## Agent Strategy That Worked

1. **3 parallel Explore agents** for initial codebase coverage (~2 min total):
   - Core struct patterns agent
   - Consumer patterns agent (autograd/training/data)
   - Language feature verification agent

2. **2 parallel Plan agents** for review analysis (~4 min total):
   - Feasibility & safety gaps agent
   - Phase ordering & scope agent

3. **1 Explore agent** for package split dependency analysis (~1 min)

4. **Targeted file reads** to verify agent claims before committing to architecture

Total exploration time: ~7 minutes for comprehensive analysis of a 15,700-line migration.
