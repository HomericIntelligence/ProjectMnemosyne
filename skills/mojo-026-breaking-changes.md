---
name: mojo-026-breaking-changes
description: "Catalog of Mojo 0.26.3 breaking changes and fixes. Use when: (1) migrating a Mojo codebase from 0.26.1 to 0.26.3, (2) encountering unfamiliar compile errors after a Mojo version bump, (3) auditing code for deprecated APIs."
category: tooling
date: 2026-04-08
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [mojo, breaking-changes, migration, 0.26.3, deprecation]
---

# Mojo 0.26.3 Breaking Changes Catalog

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-08 |
| **Objective** | Document all breaking changes and deprecation warnings introduced in Mojo 0.26.3 vs 0.26.1, with exact fixes |
| **Outcome** | Catalog extracted from migration attempt on ~525 .mojo files / 7807 fn definitions in ProjectOdyssey |
| **Verification** | unverified — migration still in progress; CI validation pending |

## When to Use

- Encountering compile errors after upgrading from Mojo 0.26.1 → 0.26.3
- Need to know if a specific error is a hard error or just a deprecation warning
- Performing a bulk migration and need a comprehensive checklist of what to fix
- Reviewing a PR that touches Mojo version-sensitive code

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end (verification: unverified). Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# Get unique error categories first (sort -u avoids noise)
mojo package -I . shared -o /tmp/shared.mojopkg 2>&1 | grep ": error:" | sort -u

# Or for the full package build via pixi (avoids permission issues with build/debug/)
pixi run mojo package -I . shared -o /tmp/shared.mojopkg 2>&1 | grep ": error:" | sort -u

# Check for deprecation warnings separately
pixi run mojo package -I . shared -o /tmp/shared.mojopkg 2>&1 | grep ": warning:" | sort -u
```

### Breaking Change Reference Table

| # | Change | Severity | Error Message | Fix |
|---|--------|----------|---------------|-----|
| 1 | `fn` keyword deprecated | WARNING | `warning: 'fn' is deprecated, use 'def' instead` | Replace `fn` with `def` (NOT a blocking error in 0.26.3) |
| 2 | `@register_passable("trivial")` removed | HARD ERROR | `decorator @register_passable("trivial") is removed, conform to TrivialRegisterPassable trait instead` | Change decorator to struct inheritance: `struct Foo(TrivialRegisterPassable):` |
| 3 | `@escaping` closure decorator removed | HARD ERROR | `the 'escaping' function effect is no longer supported; use 'unified' closures instead` | Remove `@escaping` from closure parameters |
| 4 | `Stringable`/`Representable` renamed | HARD ERROR | `use of unknown declaration 'Stringable'`, `use of unknown declaration 'Representable'` | Use `Writable` trait instead |
| 5 | `String.__getitem__` slice API changed | HARD ERROR | `no matching method in call to '__getitem__'` | Old: `s[start:end]`. New: `String(s[byte=start:end])` — `byte:` is keyword-only, returns `StringSlice`; wrap with `String()` for owned string. No `substr` method exists. |
| 6 | `ImplicitlyCopyable` + `List` fields | HARD ERROR | `cannot synthesize copy constructor because field '_shape' has non-copyable type 'List[Int]'` | `List[T]` is `Copyable` but NOT `ImplicitlyCopyable`. Fix: replace `List[Int]` fields with `InlineArray[Int, MAX_N]` + `_ndim: Int` counter, OR remove `ImplicitlyCopyable` from trait list (causes cascade callsite errors). |
| 7 | Nested capturing functions | HARD ERROR | `capturing nested functions must be declared 'unified'` | Add `@parameter` decorator or restructure closures |
| 8 | `UnsafePointer[Byte]` origin parameters | HARD ERROR | `value passed to 'data' cannot be converted from 'UnsafePointer[Byte, origin_of(content)]' to 'UnsafePointer[UInt8, MutAnyOrigin]'` | Origin parameters now required; use `UnsafePointer[UInt8, ...]` with explicit origins |
| 9 | `__copyinit__` deprecated | DEPRECATION | (varies) | New pattern: `def __init__(out self, *, copy: Self):` — old `__copyinit__` still works in 0.26.3 |
| 10 | Implicit stdlib imports | DEPRECATION | `Implicit standard library imports are deprecated; fully qualify with 'std.' instead` | Use `from std.collections import List` instead of `from collections import List` |
| 11 | `var` in parameter lists removed | HARD ERROR | (varies) | Remove `var` from `fn foo(var data: List[Int])` → `fn foo(data: List[Int])` |
| 12 | Math functions need dtype constraints | HARD ERROR | `invalid call to 'exp': lacking evidence to prove correctness` | Callers must be in `@parameter if dtype == DType.float32:` branches or have explicit float type constraints |
| 13 | Import scope restriction | HARD ERROR | `import statements are only supported at module or function scope` | Move imports from inside struct bodies to module top level or function scope |
| 14 | Circular re-export references | HARD ERROR | `attempt to resolve a recursive reference to declaration` | `shared/__init__.mojo` re-exporting through `shared/core/__init__.mojo` creates circular references in the new import resolver; flatten re-exports |

### Detailed Steps

1. Run `mojo package ... 2>&1 | grep ": error:" | sort -u` to get a unique list of error categories
2. Address hard errors in dependency order: core types first, then dependent modules, then tests/examples
3. Handle `@register_passable("trivial")` → add trait to struct declaration line
4. Handle `ImplicitlyCopyable` + `List` fields with the `InlineArray` approach (preferred) or by dropping `ImplicitlyCopyable`
5. Fix `String.__getitem__` slices — always wrap in `String()` to get an owned string back
6. Fix import placement (no struct-body imports)
7. Fix circular re-exports in `__init__.mojo` files
8. Run again to confirm no remaining errors, then address deprecation warnings separately

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Probing API via test .mojo files | Created small test files to discover correct API | Slow and distracting; each file requires a full compile cycle | Fetch official docs at `https://docs.modular.com/mojo/std/` instead |
| `str_slice` helper for String slicing | Added a helper function wrapping the new slice API | User explicitly rejected as engineering debt | Use `String(s[byte=start:end])` directly at callsites |
| Removing `ImplicitlyCopyable` from `AnyTensor` | Dropped trait to satisfy `List[T]` field constraint | Caused 62-file cascade of implicit copy errors across entire codebase | Prefer `InlineArray` fix; only remove `ImplicitlyCopyable` if the cascade is acceptable |
| `sed` for bulk `fn` → `def` replacement | Used sed to replace `fn` keyword globally | Would change `fn` inside comments, strings, and identifiers | Use AST-aware tool or targeted regex that matches `fn ` (with space) at line start |

## Results & Parameters

### ImplicitlyCopyable + List Fix Pattern

```mojo
# BEFORE (breaks in 0.26.3)
@value
struct Shape(ImplicitlyCopyable):
    var _data: List[Int]
    var _ndim: Int

# AFTER — use InlineArray with fixed max (8 is sufficient for ML tensors)
alias MAX_DIMS = 8

@value
struct Shape(ImplicitlyCopyable, TrivialRegisterPassable):
    var _data: InlineArray[Int, MAX_DIMS]
    var _ndim: Int
```

### String Slice Fix Pattern

```mojo
# BEFORE (breaks in 0.26.3)
var sub = s[start:end]

# AFTER
var sub = String(s[byte=start:end])
```

### @register_passable Fix Pattern

```mojo
# BEFORE (breaks in 0.26.3)
@register_passable("trivial")
struct Point:
    var x: Float32
    var y: Float32

# AFTER
struct Point(TrivialRegisterPassable):
    var x: Float32
    var y: Float32
```

### Import Scope Fix Pattern

```mojo
# BEFORE (breaks in 0.26.3 — import inside struct body)
struct Foo:
    from some.module import Bar
    var field: Bar

# AFTER
from some.module import Bar

struct Foo:
    var field: Bar
```

### Stdlib Import Fix Pattern

```mojo
# BEFORE (deprecation warning)
from collections import List
from algorithm import vectorize

# AFTER
from std.collections import List
from std.algorithm import vectorize
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Mojo 0.26.1 → 0.26.3 migration attempt, ~525 .mojo files, 7807 fn definitions | Migration in progress; errors confirmed from compiler output |
