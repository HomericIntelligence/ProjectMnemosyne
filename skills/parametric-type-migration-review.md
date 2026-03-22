---
name: parametric-type-migration-review
description: "Systematic review methodology for planning large-scale parametric type system migrations in Mojo. Use when: reviewing compile-time parameterization of runtime-typed structs, dependency analysis for package splits, zero-copy conversion safety, or phased migration orchestration."
category: architecture
date: 2026-03-21
version: 1.0.0
user-invocable: false
---

# Parametric Type Migration Review

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-03-21 |
| **Objective** | Review and revise a plan to split a 4,700-line runtime-typed tensor (ExTensor) into compile-time Tensor[dtype: DType] + runtime AnyTensor in Mojo 0.26.1 |
| **Outcome** | Found 4 blockers, 8 high, 6 medium, 4 low issues; designed 3-layer package split; revised 7-phase plan into 17 sub-phases; revised scope from 9,700 to 15,700 lines |
| **Context** | Mojo ML framework (ProjectOdyssey) — epic #4998, ~569 importing files, 395 test files, 4,793 ExTensor references |

## When to Use This Skill

- Reviewing a plan to convert runtime-typed fields to compile-time type parameters
- Analyzing whether zero-copy conversions between typed and type-erased types are memory-safe
- Designing package architecture to avoid circular dependencies when splitting a monolithic module
- Estimating scope for a codebase-wide type migration (especially parametric types in Mojo)
- Planning parallel sub-agent work with worktrees for phased migrations
- Identifying which Mojo 0.26.1 features work vs. don't work for parametric design patterns

## Verified Workflow

### Quick Reference

1. Read the plan thoroughly — understand the dual-type architecture before reviewing
2. Launch parallel exploration agents (3 simultaneous) for codebase coverage
3. Launch parallel plan agents (2 simultaneous) for feasibility + phase ordering analysis
4. Cross-reference findings against codebase with targeted file reads
5. Ask user key design questions (package placement, rename timing, test volume)
6. Integrate findings into plan document in-place
7. Update the tracking epic with overview + attached plan

### Step 1: Parallel Codebase Exploration (3 agents)

Launch 3 Explore agents simultaneously:

**Agent 1 — Core struct patterns**: Read the target struct, key methods (`__getitem__`, `set()`, internal accessors), operator dispatch pattern, SIMD activation patterns, lazy expression system, shape manipulation List usage, trait definitions.

**Agent 2 — Consumer patterns**: Read autograd (Variable, optimizers, tape), training (mixed_precision, gradient_ops), data (Dataset, Batch, cache), layer structs, gradient types. Focus on how the target type is stored in struct fields and collections.

**Agent 3 — Language feature verification**: Search for existing usage of auto-parameterization (count instances), comptime aliases, Variant, @parameter if, rebind, parametric structs, bitcast patterns, import structure. Count references in tests.

### Step 2: Parallel Plan Review (2 agents)

**Agent A — Feasibility & safety gaps**: Check naming collisions in __init__.mojo, module placement circular deps, zero-copy refcount safety, operator overload correctness on parametric structs, trait boundary limitations, lazy expression dependencies.

**Agent B — Phase ordering & scope**: Verify phase dependencies (especially trait→layer ordering), check scope estimates against actual grep counts, recommend PR splitting strategy, assess compilation time risk.

### Step 3: Critical File Verification

After plan agents return, read the specific files they flagged:
- Refcount protocol (`__copyinit__`, `__del__`) in the target struct
- Naming collisions in `__init__.mojo` files
- Trait signatures that reference the target type
- Import statements to verify dependency analysis claims

### Step 4: User Design Questions

Ask about: package placement, file rename timing, test volume handling strategy.

### Step 5: Integrate and Publish

- Edit the plan document in-place (not a separate review doc)
- Post overview comment on tracking epic
- Attach full plan to epic (use `<details>` collapse for large docs)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Separate review document | Created standalone review doc as deliverable | User wanted findings integrated directly into the plan, not a separate file | Ask delivery format preference before creating new files. In-place integration is often preferred. |
| 2-layer package split | Proposed Tensor[dtype] in shared/tensor/ separate from ExTensor in shared/core/ | User wanted 3-layer split with base layer for zero-dependency utilities. 2-layer also creates circular deps. | Ask about package architecture early. Verify circular dep freedom by tracing actual imports, not conceptual analysis. |
| Auto-parameterization assumption | Plan assumed `fn relu(t: Tensor) -> Tensor` would auto-parameterize | Mojo 0.26.1 auto-parameterization fails for return types. Codebase had 0 existing uses — strong signal. | Always verify language feature claims by checking existing usage count. Zero existing uses = likely doesn't work. |
| Single-phase scope estimates | Original plan estimated ~200 lines for rename, ~3,000 for tests | Rename touches 4,703-line file + 569 importers (~1,500). Tests have 3,975 creation calls (~5,600). | Cross-reference scope estimates against actual grep counts. Multiply by 1.5-3x, not 1x. |

## Results & Parameters

### Blocker Categories for Parametric Type Migrations

```yaml
naming_collision:
  description: "Existing comptime alias conflicts with new struct name"
  detection: "grep for 'comptime <NewTypeName>' in __init__.mojo files"
  fix: "Remove alias BEFORE creating new struct"

refcount_protocol:
  description: "Zero-copy conversion between typed and type-erased must share refcount"
  detection: "Check if as_typed()/as_erased() increments shared _refcount"
  fix: "Internal constructor takes shared refcount pointer, increments on construction"
  test: "Create source, convert, let source die, verify target data intact"

trait_boundary:
  description: "Mojo 0.26.1 can't parameterize trait methods"
  detection: "Check which structs implement traits with target type in signatures"
  fix: "Traits stay on type-erased type; type safety only inside implementations"

scope_underestimate:
  description: "Reference count != actual lines changed"
  detection: "grep -c for type name in all files, multiply by 1.5-3x"
  fix: "Split large phases into sub-PRs, estimate per-directory"
```

### 3-Layer Package Architecture Pattern

```yaml
layer_1_base:
  contents: "Constants, memory pool, broadcasting, dtype ordinal, error utils, type aliases"
  rule: "Zero imports from layer 2 or 3"
  detection: "grep imports in each candidate — must find zero deps on target type"

layer_2_tensor:
  contents: "Typed tensor, type-erased tensor, traits, gradient containers, validation, I/O"
  rule: "Imports from layer 1 only"

layer_3_core:
  contents: "All operations, layers, module traits, sequential containers"
  rule: "Imports from layers 1 and 2"
```

### Phase Ordering Rules

```yaml
traits_before_module_layers:
  rule: "Update trait signatures BEFORE parameterizing structs that implement those traits"
  detection: "grep for trait conformance on target structs"

file_rename_last:
  rule: "Defer file renames to final cleanup phase"
  reason: "Avoids breaking N import paths early"

package_split_first:
  rule: "Move files to new packages BEFORE adding new types"
  reason: "Ensures clean dependency chains from the start"
```

### Parallel Execution Windows

```yaml
window_1: [phase_3a, phase_3b, phase_3c, phase_3d]  # Core ops by category
window_2: [phase_5b, phase_5c]  # Collections + optimizer
window_3: [phase_7a, phase_7b, phase_7c, phase_7d]  # Tests by directory
```
