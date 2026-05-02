# Session Notes: Mojo Sequential Parametric Containers

## Session Date
2026-03-07

## Issue
GitHub issue #3218 — "Implement Sequential module for composing neural network layers"

## Context
ML Odyssey project. `Module` trait exists in `shared/core/module.mojo`. Need a
`Sequential` container that composes `Module` implementations and chains forward passes.
Referenced in module docstring example but not implemented.

## Repository State
- Branch: `3218-auto-impl`
- PR: #3737 (HomericIntelligence/ProjectOdyssey)
- Files changed: 3 (sequential.mojo, test_sequential.mojo, __init__.mojo)

## Key Discovery: Mojo Cannot Do Dynamic List[Module]
Mojo v0.26.1 does not support trait objects in `List` without `ImplicitlyCopyable`.
The Module trait defines methods but structs implementing it may not satisfy that
constraint. Dynamic dispatch via a heterogeneous list is not possible without unsafe
pointer indirection.

## Solution: Parametric Structs
Use `struct Sequential2[T0: Module, T1: Module](Movable)` — types resolved at compile
time, no heap indirection required. Ownership transfer uses `^` operator throughout.

Only `Movable` trait added (not `Copyable`) to avoid forcing contained layer types to
implement `ImplicitlyCopyable`.

## Test Strategy
- Local dummy structs (`ScaleModule`, `IdentityModule`, `DummyModuleWithParams`)
  isolate Sequential logic from real layer behavior
- FP-representable values used: 0.5, 0.25, 0.125 for deterministic checks
- Cannot run `mojo test` locally (GLIBC incompatibility on Debian 10 host)
- Pre-commit hooks all pass, CI will validate actual compilation

## Pre-commit Output (All Passed)
```
Mojo Format..............................................................Passed
Check for deprecated List[Type](args) syntax.............................Passed
Validate Test Coverage...................................................Passed
Trim Trailing Whitespace.................................................Passed
Fix End of Files.........................................................Passed
Check for Large Files....................................................Passed
Fix Mixed Line Endings...................................................Passed
```
