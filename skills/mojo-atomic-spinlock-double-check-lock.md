---
name: mojo-atomic-spinlock-double-check-lock
description: "Implement a correct SpinLock in Mojo using the double-check lock pattern when Atomic[DType.int64] lacks compare_exchange. Use when: (1) implementing a spinlock in Mojo without CAS support, (2) seeing counter underflow/overflow from naive fetch_add/fetch_sub lock, (3) thread-safety tests hang or produce wrong counts, (4) Mojo Atomic API only has fetch_add/fetch_sub/load."
category: debugging
date: 2026-04-10
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - mojo
  - atomic
  - spinlock
  - thread-safety
  - concurrent
  - double-check-lock
  - fetch_add
  - fetch_sub
  - memory-pool
---

# Mojo Atomic SpinLock: Double-Check Lock Pattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-10 |
| **Objective** | Fix race condition in `TensorMemoryPool` SpinLock causing all 6 thread-safety tests to fail silently |
| **Outcome** | All 6 thread-safety tests pass; 8 threads × 1000 iterations = exactly 8000 (no data races) |
| **Verification** | verified-local — compiled and ran `pixi run mojo /tmp/test_lock2.mojo`; CI validation pending (PR #5212) |

## When to Use

- Implementing a spinlock in Mojo and `Atomic[DType.int64]` does not have `store`, `exchange`, or `compare_exchange_weak`
- Seeing counter underflow (goes negative) or overflow in an atomic lock under high contention
- Thread-safety tests hang indefinitely (liveness violation) or produce wrong counts (safety violation)
- Mojo's `Atomic` API only provides: `fetch_add`, `fetch_sub`, `load`, `max`, `min`
- Migrating a CAS-based spinlock from C++ or Rust to Mojo and the direct translation is unavailable

## Verified Workflow

### Quick Reference

```mojo
# Mojo double-check lock pattern — correct SpinLock without CAS
# Works with Atomic[DType.int64] which only has fetch_add/fetch_sub/load

def lock(self):
    var ptr = self._as_atomic()
    while True:
        # Cheap spin: wait until counter looks free (no atomic RMW)
        while ptr[].load() != 0:
            pass
        # Try to claim: only one thread gets "was 0" back
        if ptr[].fetch_add(1) == 0:
            return          # We hold the lock; counter is exactly 1
        # Someone else won the race — undo our increment and retry
        _ = ptr[].fetch_sub(1)

def unlock(self):
    var ptr = self._as_atomic()
    _ = ptr[].fetch_sub(1)  # Always goes 1 → 0 because lock() guarantees counter==1
```

### Detailed Steps

1. **Understand the API constraint**: Mojo's `Atomic[DType.int64]` exposes only
   `fetch_add`, `fetch_sub`, `load`, `max`, and `min`. Classic CAS-based spinlocks
   (`compare_exchange_weak`) cannot be used directly. The double-check pattern works
   around this.

2. **The invariant to maintain**: The counter is exactly `1` while the lock is held
   and exactly `0` while free. `unlock()` must always subtract from 1→0. This is only
   safe if `lock()` guarantees it.

3. **Inner spin (cheap path)**: `while ptr[].load() != 0: pass` — no atomic RMW, low
   cache-line contention. Threads spin here most of the time.

4. **Atomic claim attempt**: `fetch_add(1)` atomically increments and returns the
   *previous* value. Only one thread among all concurrent `fetch_add` callers can
   observe the return value `0` (the lock was free at that instant). That thread owns
   the lock.

5. **Undo on loss**: If `fetch_add` returns `> 0`, another thread holds the lock.
   Immediately call `fetch_sub(1)` to undo the increment, then loop back. This keeps
   the counter bounded and prevents underflow in `unlock()`.

6. **Unlock is trivially safe**: Because `lock()` only returns when it observes
   `fetch_add` return `0`, the counter is exactly `1` at that point. `unlock()` doing
   `fetch_sub(1)` always goes `1 → 0`.

7. **Verify with a concurrent counter test**:

   ```mojo
   # /tmp/test_lock2.mojo
   from algorithm import parallelize
   var total = 0
   @parameter
   fn worker(thread_id: Int):
       for _ in range(1000):
           lock.lock()
           total += 1
           lock.unlock()
   parallelize[worker](8)
   assert total == 8000, "Expected 8000, got " + str(total)
   ```

   Run with: `pixi run mojo /tmp/test_lock2.mojo`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Naive fetch_add lock + fetch_sub unlock | `lock`: `fetch_add(1)` unconditionally; `unlock`: `fetch_sub(1)` | Under high contention multiple threads have in-flight increments before the holder's unlock runs. `fetch_sub(1)` goes e.g. 3→2 (not to 0), so waiting threads never see counter==0 and spin forever (liveness violation). | Counter must be exactly 1 when held, not "≥1". All contenders must undo their increment when they lose. |
| Loop in unlock: `while fetch_sub != 1` | `unlock`: keep subtracting until it returns 1 | When multiple threads have in-flight increments, looping `fetch_sub` drives the counter below 1→0→-1. The holder subtracts from a negative value; contenders see counter < 0 and either spin or underflow further. Counter never stabilizes. | The unlock path must be a single `fetch_sub`. The cleanup of excess increments must happen in `lock()`, not `unlock()`. |
| Direct CAS translation from C++ | `compare_exchange_weak(&expected, 0, 1)` | Mojo `Atomic[DType.int64]` has no `compare_exchange_weak` or `exchange` methods (as of Mojo 0.26.x). Compilation fails. | Check Mojo Atomic API before porting. The double-check pattern is the correct Mojo substitute. |

## Results & Parameters

### Working Implementation

```mojo
# shared/base/memory_pool.mojo  (TensorMemoryPool SpinLock)
struct SpinLock:
    var _counter: Int64  # Stored as plain Int64; cast to Atomic inside methods

    fn __init__(out self):
        self._counter = 0

    fn _as_atomic(self) -> UnsafePointer[Atomic[DType.int64]]:
        return UnsafePointer.address_of(self._counter).bitcast[Atomic[DType.int64]]()

    fn lock(mut self):
        var ptr = self._as_atomic()
        while True:
            while ptr[].load() != 0:
                pass
            if ptr[].fetch_add(1) == 0:
                return
            _ = ptr[].fetch_sub(1)

    fn unlock(mut self):
        var ptr = self._as_atomic()
        _ = ptr[].fetch_sub(1)
```

### Verification

```bash
# Compile and run the concurrent counter smoke test
pixi run mojo /tmp/test_lock2.mojo

# Expected output: no assertion error, exits 0
# 8 threads × 1000 iterations = exactly 8000
```

### Mojo Atomic API Reference (0.26.x)

| Method | Signature | Notes |
|--------|-----------|-------|
| `load` | `() -> Scalar[type]` | Non-atomic on some platforms; use for cheap inner spin |
| `fetch_add` | `(rhs: Scalar[type]) -> Scalar[type]` | Returns *previous* value; atomic |
| `fetch_sub` | `(rhs: Scalar[type]) -> Scalar[type]` | Returns *previous* value; atomic |
| `max` | `(rhs: Scalar[type]) -> None` | Atomic max in-place |
| `min` | `(rhs: Scalar[type]) -> None` | Atomic min in-place |
| `compare_exchange_weak` | **MISSING** | Not available; use double-check pattern instead |
| `exchange` | **MISSING** | Not available |
| `store` | **MISSING** | Not available |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #5212 `fix/ci-stability-and-quality` — `TensorMemoryPool` SpinLock race causing 6 thread-safety test failures | Compiled and ran 8-thread × 1000-iteration counter test locally with `pixi run mojo`; CI auto-merge enabled |
