---
name: mojo-026-breaking-changes
description: "Catalog of Mojo 0.26.3 breaking changes and fixes. Use when: (1) migrating a Mojo codebase from 0.26.1 to 0.26.3, (2) encountering unfamiliar compile errors after a Mojo version bump, (3) auditing code for deprecated APIs."
category: tooling
date: 2026-04-08
version: "2.0.0"
user-invocable: false
verification: verified-local
history: mojo-026-breaking-changes.history
tags: [mojo, breaking-changes, migration, 0.26.3, deprecation, capturing, ImplicitlyDestructible, substr]
---

# Mojo 0.26.3 Breaking Changes Catalog

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-08 |
| **Objective** | Document all breaking changes and deprecation warnings introduced in Mojo 0.26.3 vs 0.26.1, with exact fixes |
| **Outcome** | Zero compile errors confirmed locally on ~525 .mojo files / 7807 fn definitions in ProjectOdyssey (PR #5207) |
| **Verification** | verified-local — zero compile errors confirmed; CI validation in progress |
| **History** | [changelog](./mojo-026-breaking-changes.history) |

## When to Use

- Encountering compile errors after upgrading from Mojo 0.26.1 → 0.26.3
- Need to know if a specific error is a hard error or just a deprecation warning
- Performing a bulk migration and need a comprehensive checklist of what to fix
- Reviewing a PR that touches Mojo version-sensitive code

## Verified Workflow

### Quick Reference

```bash
# Get unique error categories first (sort -u avoids noise)
pixi run mojo package -I . shared -o /tmp/shared.mojopkg 2>&1 | grep ": error:" | sort -u

# Check for deprecation warnings separately
pixi run mojo package -I . shared -o /tmp/shared.mojopkg 2>&1 | grep ": warning:" | sort -u
```

### Breaking Change Reference Table

| # | Change | Severity | Error Message | Fix |
|---|--------|----------|---------------|-----|
| 1 | `fn` keyword deprecated | WARNING only | `warning: 'fn' is deprecated, use 'def' instead` | Replace `fn` with `def` — NOT a hard error in 0.26.3, still compiles |
| 2 | `@register_passable("trivial")` removed | HARD ERROR | `decorator @register_passable("trivial") is removed, conform to TrivialRegisterPassable trait instead` | Change to struct inheritance: `struct Foo(TrivialRegisterPassable):` |
| 3 | `escaping` function effect removed | HARD ERROR | `the 'escaping' function effect is no longer supported` | See capturing closure section below — requires compile-time parametric approach |
| 4 | `Stringable`/`Representable` renamed | HARD ERROR | `use of unknown declaration 'Stringable'` | Use `Writable` trait instead |
| 5 | `String.substr()` removed | HARD ERROR | `'String' value has no attribute 'substr'` | Use `String(s[byte=start:end])` — `byte:` is keyword-only, returns `StringSlice`; wrap with `String()` |
| 6 | `ImplicitlyCopyable` + `List` fields | HARD ERROR | `cannot synthesize copy constructor because field '_shape' has non-copyable type 'List[Int]'` | Use `InlineArray[Int, MAX_N]` + `_ndim: Int`, OR remove `ImplicitlyCopyable` (causes cascade) |
| 7 | Traits in generic contexts need `ImplicitlyDestructible` | HARD ERROR | `abandoned without being explicitly destroyed: unhandled explicitly destroyed type 'X'` | Add `(ImplicitlyDestructible)` to the trait definition — see cascade section below |
| 8 | `UnsafePointer[UInt8]` missing origin | HARD ERROR | `failed to infer parameter 'origin'` | Change to `UnsafePointer[UInt8, _]` to unbind the origin parameter |
| 9 | `__moveinit__` with `deinit other` field access | HARD ERROR | `'None' has no attributes` on `other.field^` | Remove `__moveinit__` entirely — `Movable` trait provides automatic move without it |
| 10 | Capturing closures as runtime values | HARD ERROR | `TODO: capturing closures cannot be materialized as runtime values` | Pass capturing closures as compile-time parameters (see capturing section) |
| 11 | `var` in parameter lists removed | HARD ERROR | (varies) | Remove `var` from `fn foo(var data: List[Int])` → `fn foo(data: List[Int])` |
| 12 | Import scope restriction | HARD ERROR | `import statements are only supported at module or function scope` | Move imports from inside struct bodies to module top level or function scope |
| 13 | `__copyinit__` deprecated | DEPRECATION | (varies) | New pattern: `def __init__(out self, *, copy: Self):` — old `__copyinit__` still works in 0.26.3 |
| 14 | Circular re-export references | HARD ERROR | `attempt to resolve a recursive reference to declaration` | Flatten re-exports in `__init__.mojo` files |

### Detailed Steps

1. Run `pixi run mojo package ... 2>&1 | grep ": error:" | sort -u` to get unique error categories
2. Fix `ImplicitlyDestructible` cascade on traits first (before fixing callsites)
3. Fix capturing closures (gradient_checker pattern) — requires compile-time param approach
4. Fix `String.substr()` → `String(s[byte=start:end])`
5. Fix `UnsafePointer[UInt8]` → `UnsafePointer[UInt8, _]`
6. Remove broken `__moveinit__` with `deinit other`
7. Run again to confirm zero errors, then address deprecation warnings

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `fn(AnyTensor) raises capturing -> AnyTensor` as param type | Used `capturing` as type in `[ForwardFn: fn(AnyTensor) raises capturing -> AnyTensor]` | "expected a type, not a value" — wrong ordering | Correct ordering is `fn(AnyTensor) capturing raises -> AnyTensor` with `capturing` BEFORE `raises` |
| `unified {}` empty capture list | Changed closures to `fn forward(x) raises unified {} -> AnyTensor` | "Could not infer capture convention" | Use `capturing` keyword, not `unified {}` |
| `unified {mut}` capture list | Changed to `unified {mut}` for outer variable access | "Cannot capture X by mut because value is immutable" | Immutable outer vars cannot use `mut`; use `capturing` which captures by value |
| `def(AnyTensor) raises -> AnyTensor` as param type | Used `def` instead of `fn` for closure type | Closure type mismatch at callsite | Must use `fn` for compile-time closure params |
| `__moveinit__` field access with `^` under `deinit other` | `self.name = other.name^` inside `fn __moveinit__(out self, deinit other: Self)` | `'None' has no attributes` — `deinit` already consumes the value | Remove `__moveinit__` entirely; `Movable` provides auto-move |
| Taking HEAD version of substr conflicts during rebase | Resolved rebase conflicts by taking HEAD which had `.substr()` | HEAD had the old API; `.substr()` does not exist in 0.26.3 | The local commit with `String(x[byte=...])` was the correct 0.26.3 syntax |
| Probing API via test .mojo files | Created small test files to discover correct API | Slow; each file requires a full compile cycle | Fetch official docs instead |
| Removing `ImplicitlyCopyable` from `AnyTensor` | Dropped trait to satisfy `List[T]` field constraint | Caused 62-file cascade of implicit copy errors | Prefer `InlineArray` fix or add `ImplicitlyDestructible` to affected traits |

## Results & Parameters

### Capturing Closures as Compile-Time Parameters (NEW in 0.26.3)

The `escaping` keyword is completely removed. Higher-order functions that accept closures must use compile-time parameters:

```mojo
# BEFORE (broken in 0.26.3)
fn check_gradients(
    forward_fn: fn(AnyTensor) raises escaping -> AnyTensor,
    input: AnyTensor,
) raises -> Bool:
    var result = forward_fn(input)

# AFTER (0.26.3 — capturing BEFORE raises)
fn check_gradients[
    forward_fn: fn(AnyTensor) capturing raises -> AnyTensor,
](
    input: AnyTensor,
) raises -> Bool:
    var result = forward_fn(input)

# Callsite: closure in [square brackets]
fn my_forward(x: AnyTensor) capturing raises -> AnyTensor:
    return relu(x)

var passed = check_gradients[my_forward](input)
```

### ImplicitlyDestructible Cascade

When a trait is used in a generic function or struct, add `ImplicitlyDestructible`:

```mojo
# BEFORE — causes "abandoned without being explicitly destroyed" errors
trait Module:
    fn forward(mut self, input: AnyTensor) raises -> AnyTensor: ...

# AFTER
trait Module(ImplicitlyDestructible):
    fn forward(mut self, input: AnyTensor) raises -> AnyTensor: ...
```

Traits that needed this in ProjectOdyssey: `Module`, `ReduceOp`, `ReduceBackwardOp`,
`ElementwiseUnaryOp`, `ElementwiseBinaryOp`, `Differentiable`, `Model`, `Loss`,
`Optimizer`, `Dataset`, `Sampler`, `Transform`. Also `Sequential2/3/4/5` structs.

### String Slice Fix Pattern

```mojo
# BEFORE (no substr method in 0.26.3)
var sub = s.substr(start, length)
var end_char = s.substr(0, len(s) - 1)

# AFTER
var sub = String(s[byte=start:start+length])
var end_char = String(s[byte=0:len(s)-1])
var rest = String(s[byte=start:len(s)])  # from position to end
```

### UnsafePointer Origin Fix

```mojo
# BEFORE
fn _bytes_to_hex(data: UnsafePointer[UInt8], ...) -> String:

# AFTER
fn _bytes_to_hex(data: UnsafePointer[UInt8, _], ...) -> String:
```

### __moveinit__ Fix

```mojo
# BEFORE (broken — 'None' has no attributes on field^)
fn __moveinit__(out self, deinit other: Self):
    self.name = other.name^
    self.tensor = other.tensor^

# AFTER — remove __moveinit__ entirely
# Movable trait provides automatic move constructor
struct NamedTensor(Movable):
    var name: String
    var tensor: AnyTensor
    # No __moveinit__ needed
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Mojo 0.26.1 → 0.26.3 migration, ~525 .mojo files, PR #5207 | Zero compile errors confirmed locally on branch fix-ci-root-causes |
