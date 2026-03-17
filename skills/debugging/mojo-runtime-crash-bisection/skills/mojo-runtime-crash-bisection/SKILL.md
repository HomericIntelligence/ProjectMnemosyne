---
name: mojo-runtime-crash-bisection
description: "Systematic approach for bisecting Mojo runtime crashes to create minimal reproducers and isolate root causes. Use when: Mojo crashes in runtime libraries, need upstream bug reports."
category: debugging
date: 2026-03-16
user-invocable: false
---

# Mojo Runtime Crash Bisection

## Overview

| Attribute | Value |
|-----------|-------|
| Category | debugging |
| Language | Mojo 0.26.1 |
| Complexity | High |
| Time to Apply | 2-4 hours |
| Prerequisite | Reproducible Mojo crash |

Systematic methodology for reducing a Mojo runtime crash from a large codebase
to a minimal, self-contained reproducer suitable for filing upstream issues against
`modular/modular`. The approach uses binary reduction across multiple dimensions
(code volume, struct fields, function scoping, allocation patterns) to isolate the
exact trigger.

## When to Use

- Mojo program crashes with stack traces in `libKGENCompilerRTShared.so` or `libAsyncRTRuntimeGlobals.so`
- Crash output is just `execution crashed` with no helpful error message
- Need to determine if a crash is user error or a Mojo runtime bug
- Creating a bug report for the Modular team that requires a minimal reproducer
- Crash is non-obvious (not a simple null pointer or bounds violation)

## Verified Workflow

### Quick Reference

```text
1. Characterize  → Run N times, capture stack traces, note determinism
2. Reduce scope  → Strip to 1 test/function that still crashes
3. Reduce ops    → Remove operations until crash boundary found
4. Reduce struct → Remove struct fields to isolate which field matters
5. Verify user code → Add bounds checks, trace refcounts, test move semantics
6. Inline deps   → Create self-contained reproducer with zero imports
7. File upstream → Include reproducer, isolation experiments table, stack trace
```

### Step 1: Characterize the Crash

Run the crashing code 5+ times and record:

- Is the crash deterministic (same stack offsets every run)?
- Does the crash happen before or after any output? (Before = compile/import issue; after = runtime)
- Which libraries appear in the stack trace?

A crash with **identical offsets** across runs indicates deterministic heap corruption, not a random race.

### Step 2: Binary Reduction — Code Volume

Start from the full failing test and systematically remove code:

1. Strip to 1 test function — does the crash persist?
2. Remove operations one at a time — find the minimum set that crashes
3. Reduce tensor/array sizes — find the minimum dimensions
4. Key insight: test **with and without** each removed piece to confirm causation

### Step 3: Binary Reduction — Function Scoping

A critical finding from this investigation: **function scope matters for destructor-triggered crashes**.

Test the same operations:
- Inline in `main()` — may NOT crash
- In separate `fn` calls from `main()` — may crash

This is because function-scoped destruction changes the order and timing of `__del__` calls.

### Step 4: Binary Reduction — Struct Fields

If the crash involves a custom struct, systematically remove fields:

```text
Original struct (crashes):
  struct Tensor:
      var _data: UnsafePointer[UInt8]
      var _shape: List[Int]        ← suspect
      var _numel: Int
      var _refcount: UnsafePointer[Int]

Reduced struct (no crash):
  struct Tensor:
      var _data: UnsafePointer[UInt8]
      var _s0: Int                 ← replaced List[Int] with fixed fields
      var _s1: Int
      var _numel: Int
      var _refcount: UnsafePointer[Int]
```

If removing a `List[Int]` field eliminates the crash, the bug is in how the runtime
handles `List` allocation/deallocation interleaved with other allocations.

### Step 5: Verify User Code Is Correct

Before filing upstream, rule out user error with explicit checks:

| Check | How |
|-------|-----|
| Bounds | Add `if idx < 0 or idx >= numel: raise` on every array access |
| Refcount | Add print statements in `__init__`/`__copyinit__`/`__moveinit__`/`__del__` |
| Move semantics | Write a `Probe` struct to verify `__del__` is NOT called after `__moveinit__` |
| Bitcast bounds | Verify `alloc_size >= index * sizeof(T)` for every bitcast write |

**Move semantics verification pattern:**

```mojo
struct Probe(Movable):
    var id: Int
    fn __init__(out self, id: Int):
        self.id = id
        print("  __init__ id=", id)
    fn __moveinit__(out self, deinit existing: Self):
        self.id = existing.id
        print("  __moveinit__ id=", self.id)
    fn __del__(deinit self):
        print("  __del__ id=", self.id)

fn main():
    var a = Probe(1)
    var b = a^  # Should print: __init__, __moveinit__, then ONE __del__
```

In Mojo 0.26.1, `deinit existing` in `__moveinit__` **suppresses** `__del__` on the source.
Only the new owner's `__del__` runs. No double-decrement.

### Step 6: Create Self-Contained Reproducer

Inline all dependencies to create a zero-import reproducer:

1. Replace library tensor structs with a minimal struct (alloc/free/refcount only)
2. Replace library conv2d with an inlined loop (sequential, single dtype)
3. Replace library relu with a simple element-wise max(0, x)
4. Keep the exact same allocation patterns and function structure

Test that the self-contained version reproduces the same crash with the same stack offsets.

### Step 7: File Upstream Issue

Structure the issue with:

1. **Environment** — Mojo version, OS, GLIBC, CPU
2. **Self-contained reproducer** — single file, zero dependencies, copy-paste-run
3. **Stack trace** — include the constant offsets
4. **Isolation experiments table** — the key evidence showing what triggers/prevents the crash
5. **Root cause hypothesis** — based on the bisection findings

The isolation experiments table is the most valuable part:

```markdown
| Variant | Crashes? | Conclusion |
|---------|----------|------------|
| Full reproducer | YES | Baseline |
| Remove bitcast write | NO | Bitcast is the trigger |
| Struct without List[Int] field | NO | List[Int] churn is the cause |
| Shapes constructed inline (no temp Lists) | NO | Temporary List churn matters |
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Raw alloc/free churn + bitcast | Created 1000 alloc/free cycles with raw `alloc[UInt8]` then bitcast write | No crash — raw allocation alone doesn't trigger the bug | The bug requires `List[Int]` internal buffer management, not just raw alloc/free |
| Pure `List[Int]` churn + bitcast | Created 1000 `List[Int]` objects, destroyed them, then did bitcast write | No crash — List churn alone doesn't trigger | Needs the combination of List-in-struct + heavy computation + bitcast |
| Assumed two separate crashes | Plan assumed `libKGENCompilerRTShared.so` and `libAsyncRTRuntimeGlobals.so` were separate crash types | Both libraries appear in the same stack trace — it is ONE crash | Always check if multiple library names in a trace are frames in a single call chain, not separate crashes |
| Building with `-debug-level=line-tables` | Tried `mojo build -debug-level=line-tables` for symbolicated traces | Linker error: undefined reference to `fmaxf` (`libm` not linked) | `mojo build` has linking limitations; `mojo run` is sufficient for crash reproduction |
| Using `^` move vs `.copy()` in `__moveinit__` | Tested if `existing._shape^` vs `existing._shape.copy()` changed crash behavior | Both crash identically | The crash is not about move vs copy semantics in `__moveinit__` |
| Reducing conv spatial size to 8x8 | Tried 8x8 spatial with 16 channels instead of 32x32 | No crash — not enough allocation volume | The crash requires sufficient allocation volume (32x32 spatial minimum with 16 channels) |
| 20x conv2d in a loop | Ran same conv2d 20 times in a `for` loop in `main()` | No crash despite heavy allocation | Function-scoped destruction (separate `fn` calls) is required, not just volume |

## Results and Parameters

### Minimum Crash Configuration

```text
Spatial size:  32x32 (8x8 does not crash)
Channels:      16 (3->16 conv)
Conv layers:   2 (in step_a)
Batch size:    2
Struct fields: Must include List[Int]
Shape helpers: Must use temporary List[Int] (shape4/shape1 functions)
Function scope: Operations must be in separate fn calls (not inline in main)
Bitcast write: Required (writing 0.0 and 1.0 to a 2-element Float32 tensor)
```

### Stack Trace Signature (constant across all runs)

```text
#0 libKGENCompilerRTShared.so  +0x3cb78b
#1 libKGENCompilerRTShared.so  +0x3c93c6
#2 libKGENCompilerRTShared.so  +0x3cc397
#3 libc.so.6                   +0x45330
#4 libAsyncRTRuntimeGlobals.so +0x416ba
```

### Filed Issue

- **Repository**: modular/modular
- **Issue**: [#6187](https://github.com/modular/modular/issues/6187)
- **Title**: Deterministic heap corruption crash: List[Int]-containing struct + heavy alloc/free + UnsafePointer.bitcast write
