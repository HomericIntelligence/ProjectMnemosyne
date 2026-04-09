---
name: mojo-026-breaking-changes
description: "Catalog of Mojo 0.26.3 breaking changes, fixes, and authoritative current syntax reference. Use when: (1) migrating a Mojo codebase from 0.26.1 to 0.26.3, (2) encountering unfamiliar compile errors after a Mojo version bump, (3) auditing code for deprecated APIs, (4) writing new Mojo code and need current syntax corrections."
category: tooling
date: 2026-04-09
version: "3.0.0"
user-invocable: false
verification: verified-local
history: mojo-026-breaking-changes.history
tags: [mojo, breaking-changes, migration, 0.26.3, deprecation, capturing, ImplicitlyDestructible, substr, syntax, modular-upstream]
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

## Authoritative Syntax Reference (Modular)

The following is Modular's canonical current Mojo syntax guide, merged from their
[official skills repo](https://github.com/modular/skills). Use this section when
writing **new** Mojo code (not just migrating). See also the Breaking Change Reference
Table above for migration-specific fixes.

### Removed Syntax — Complete Table

| Removed                                          | Replacement                                                          |
|--------------------------------------------------|----------------------------------------------------------------------|
| `alias X = ...`                                  | `comptime X = ...`                                                   |
| `@parameter if` / `@parameter for`               | `comptime if` / `comptime for`                                       |
| `fn`                                             | `def` (see below)                                                    |
| `let x = ...`                                    | `var x = ...` (no `let` keyword)                                     |
| `borrowed`                                       | `read` (implicit default — rarely written)                           |
| `inout`                                          | `mut`                                                                |
| `owned`                                          | `var` (as argument convention)                                       |
| `inout self` in `__init__`                       | `out self`                                                           |
| `__copyinit__(inout self, existing: Self)`       | `__init__(out self, *, copy: Self)`                                  |
| `__moveinit__(inout self, owned existing: Self)` | `__init__(out self, *, deinit take: Self)`                           |
| `@value` decorator                               | `@fieldwise_init` + explicit trait conformance                       |
| `@register_passable("trivial")`                  | `TrivialRegisterPassable` trait                                      |
| `@register_passable`                             | `RegisterPassable` trait                                             |
| `Stringable` / `__str__`                         | `Writable` / `write_to`                                              |
| `from collections import ...`                    | `from std.collections import ...`                                    |
| `from memory import ...`                         | `from std.memory import ...`                                         |
| `from sys import ...`                            | `from std.sys import ...`                                            |
| `from os import ...`                             | `from std.os import ...`                                             |
| `from pathlib import ...`                        | `from std.pathlib import ...`                                        |
| `s[i]`                                           | `s[byte=i]` — returns `StringSlice`; wrap in `String()` if needed    |
| `s[0:10]`, `s[:5]`                               | No slice syntax on String — use `s.codepoint_slices()` or Python FFI |
| `constrained(cond, msg)`                         | `comptime assert cond, msg`                                          |
| `DynamicVector[T]`                               | `List[T]`                                                            |
| `InlinedFixedVector[T, N]`                       | `InlineArray[T, N]`                                                  |
| `Tensor[T]`                                      | Not in stdlib (use SIMD, List, UnsafePointer)                        |

### `def` Is the Only Function Keyword

`fn` is deprecated. `def` does **not** imply `raises`. Always add `raises` explicitly:

```mojo
def compute(x: Int) -> Int:              # non-raising
    return x * 2

def load(path: String) raises -> String: # explicitly raising
    return open(path).read()
```

### `comptime` Replaces `alias` and `@parameter`

```mojo
comptime N = 1024                            # compile-time constant
comptime MyType = Int                        # type alias
comptime if condition:                       # compile-time branch
    ...
comptime for i in range(10):                 # compile-time loop
    ...
comptime assert N > 0, "N must be positive"  # must be inside function body
```

### Argument Conventions

Default is `read` (immutable borrow, never written explicitly):

```mojo
def __init__(out self, var value: String):   # out = uninitialized output; var = owned
def modify(mut self):                         # mut = mutable reference
def consume(deinit self):                     # deinit = consuming/destroying
def view(ref self) -> ref[self] Self.T:       # ref = reference with origin
```

### Lifecycle Methods

```mojo
def __init__(out self, x: Int):                    # constructor
    self.x = x
def __init__(out self, *, copy: Self):             # copy constructor
    self.data = copy.data
def __init__(out self, *, deinit take: Self):      # move constructor
    self.data = take.data^
def __del__(deinit self):                          # destructor
    self.ptr.free()
```

To copy: `var b = a.copy()` (provided by `Copyable` trait).

### Struct Patterns

```mojo
@fieldwise_init
struct Point(Copyable, Movable, Writable):
    var x: Float64
    var y: Float64

# Self-qualify struct parameters — bare names are errors
struct Container[T: Writable]:
    var data: Self.T                   # NOT T
    def size(self) -> Self.T: ...      # NOT T
```

Explicit `.copy()` or `^` required for non-`ImplicitlyCopyable` types (`Dict`, `List`).

### Imports Use `std.` Prefix

```mojo
from std.testing import assert_equal, TestSuite
from std.algorithm import vectorize
from std.python import PythonObject
```

Prelude auto-imports (no import needed): `Int`, `String`, `Bool`, `List`, `Dict`,
`Optional`, `SIMD`, `Float32`, `Float64`, `UInt8`, `Pointer`, `UnsafePointer`,
`Span`, `Error`, `DType`, `Writable`, `Writer`, `Copyable`, `Movable`, `Equatable`,
`Hashable`, `rebind`, `print`, `range`, `len`, and more.

### `Writable` / `Writer` (Replaces `Stringable`)

```mojo
struct MyType(Writable):
    var x: Int
    def write_to(self, mut writer: Some[Writer]):
        writer.write("MyType(", self.x, ")")
```

- `Some[Writer]` — builtin existential type
- Default implementations via reflection if all fields are `Writable`
- Convert to `String` with `String.write(value)`, not `str(value)`

### Collection Literals

```mojo
# WRONG — no List[T](elem1, elem2, ...) constructor
var nums = List[Int](1, 2, 3)

# CORRECT — bracket literals
var nums = [1, 2, 3]                              # List[Int]
var scores = {"alice": 95, "bob": 87}              # Dict[String, Int]
```

### Iterator Protocol

Iterators use `raises StopIteration` (not `Optional`):

```mojo
struct MyCollection(Iterable):
    comptime IteratorType[
        iterable_mut: Bool, //, iterable_origin: Origin[mut=iterable_mut]
    ]: Iterator = MyIter[origin=iterable_origin]
    def __iter__(ref self) -> Self.IteratorType[origin_of(self)]: ...
```

### Memory and Pointer Types

| Type                            | Use                                                                    |
|---------------------------------|------------------------------------------------------------------------|
| `Pointer[T, mut=M, origin=O]`   | Safe, non-nullable. Deref with `p[]`.                                  |
| `alloc[T](n)` / `UnsafePointer` | Free function `alloc[T](count)` → `UnsafePointer`. `.free()` required. |
| `Span(list)`                    | Non-owning contiguous view.                                            |
| `OwnedPointer[T]`               | Unique ownership (like Rust `Box`).                                    |
| `ArcPointer[T]`                 | Reference-counted shared ownership.                                    |

### Origin System (Not "Lifetime")

Mojo tracks reference provenance with **origins**, not "lifetimes":

```mojo
struct Span[mut: Bool, //, T: AnyType, origin: Origin[mut=mut]]: ...
```

Key types: `Origin`, `MutOrigin`, `ImmutOrigin`, `MutAnyOrigin`, `MutExternalOrigin`,
`StaticConstantOrigin`. Use `origin_of(value)` to get a value's origin.

### Numeric Conversions — Must Be Explicit

```mojo
var x = Float32(my_int) * scale    # Int → Float32
var y = Int(my_uint)               # UInt → Int
# Literals are polymorphic — auto-adapt to context
var a: Float32 = 0.5
```

### Error Handling

```mojo
def might_fail() raises -> Int:          # raises Error (default)
    raise Error("something went wrong")

def parse(s: String) raises Int -> Int:  # raises specific type
    raise 42
```

No `match` statement. No `async`/`await` — use `Coroutine`/`Task` from `std.runtime`.

### Function Types and Closures

No lambda syntax. Closures use `capturing[origins]`:

```mojo
comptime MyFunc = fn(Int) capturing[_] -> None
```

### Type Hierarchy

```text
AnyType
  ImplicitlyDestructible          — auto __del__; most types
  Movable                         — __init__(out self, *, deinit take: Self)
    Copyable                      — __init__(out self, *, copy: Self)
      ImplicitlyCopyable(Copyable, ImplicitlyDestructible)
    RegisterPassable(Movable)
      TrivialRegisterPassable(ImplicitlyCopyable, ImplicitlyDestructible, Movable, RegisterPassable)
```

---
*Authoritative Syntax Reference section adapted from [modular/skills](https://github.com/modular/skills) under Apache License 2.0. Copyright (c) Modular Inc.*

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Mojo 0.26.1 → 0.26.3 migration, ~525 .mojo files, PR #5207 | Zero compile errors confirmed locally on branch fix-ci-root-causes |
| (upstream) | Modular official skills repo | Authoritative syntax reference merged in v3.0.0 |
