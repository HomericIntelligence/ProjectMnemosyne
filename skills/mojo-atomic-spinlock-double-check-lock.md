---
name: mojo-atomic-spinlock-double-check-lock
description: "Implement a correct SpinLock in Mojo using the TTAS (Test-and-Test-and-Set) double-check lock pattern when Atomic[DType.int64] lacks compare_exchange. Use when: (1) implementing a spinlock in Mojo without CAS support, (2) seeing counter underflow/overflow from naive fetch_add/fetch_sub lock, (3) thread-safety tests hang or produce wrong counts, (4) Mojo Atomic API only has fetch_add/fetch_sub/load, (5) unlock uses store(0) instead of fetch_add(-1) — a silent race that causes permanent deadlock under TTAS contention."
category: debugging
date: 2026-04-22
version: "1.1.0"
user-invocable: false
verification: verified-precommit
tags:
  - mojo
  - atomic
  - spinlock
  - ttas
  - thread-safety
  - concurrent
  - double-check-lock
  - fetch_add
  - fetch_sub
  - store-zero-race
  - deadlock
  - memory-pool
---

# Mojo Atomic SpinLock: TTAS Double-Check Lock Pattern

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-22 (v1.1.0 amendment) |
| **Original Date** | 2026-04-10 (v1.0.0) |
| **Objective** | Fix race conditions in `TensorMemoryPool` SpinLock causing thread-safety tests to hang or deadlock |
| **Outcome v1.0.0** | All 6 thread-safety tests pass; 8 threads x 1000 iterations = exactly 8000 (no data races) |
| **Outcome v1.1.0** | CI Core Utilities C test group was timing out 100% of the time (15 min limit) due to `store(0)` unlock racing with TTAS `fetch_add(-1)` undo, driving counter to -1 — permanent deadlock. Fixed by replacing `store(0)` with `fetch_add(-1)` in `unlock()`. |
| **Verification** | verified-precommit — fix committed and pushed to `ci-main-green`; CI run in progress |

## When to Use

- Implementing a spinlock in Mojo and `Atomic[DType.int64]` does not have `store`, `exchange`, or `compare_exchange_weak`
- Seeing counter underflow (goes negative) or overflow in an atomic lock under high contention
- Thread-safety tests hang indefinitely (liveness violation) or produce wrong counts (safety violation)
- Mojo's `Atomic` API only provides: `fetch_add`, `fetch_sub`, `load`, `max`, `min`
- CI test group times out at 100% rate — spinlock deadlock typically manifests as full timeout, not a test failure
- Migrating a CAS-based spinlock from C++ or Rust to Mojo and the direct translation is unavailable
- `unlock()` uses `Atomic[DType.int64].store(self._lock_word(), Int64(0))` — this is broken for TTAS locks

## Verified Workflow

> **Note (verified-precommit)**: The fix was committed and pushed to CI but the CI run had not yet
> completed at the time of writing. The correctness argument is formal (see store(0) race explanation
> below). Await CI green before treating as `verified-ci`.

### Quick Reference

```mojo
# Mojo TTAS double-check lock — correct SpinLock without CAS
# Works with Atomic[DType.int64] which only has fetch_add/fetch_sub/load

fn lock(mut self):
    var ptr = self._as_atomic()
    while True:
        # Cheap spin: wait until counter looks free (no atomic RMW)
        while ptr[].load() != 0:
            pass
        # Try to claim: only one thread gets "was 0" back
        if ptr[].fetch_add(1) == 0:
            return          # We hold the lock; counter is exactly 1
        # Someone else won the race — undo our increment and retry
        _ = ptr[].fetch_add(-1)  # NOTE: fetch_add(-1), NOT fetch_sub(1)

fn unlock(mut self):
    var ptr = self._as_atomic()
    _ = ptr[].fetch_add(-1)  # CRITICAL: fetch_add(-1), NEVER store(0)
    # lock() guarantees counter==1 when we call unlock(), so 1->0 is exact.
    # store(0) races with a spinning thread's fetch_add(-1) undo, driving
    # the counter to -1, which the spin condition (counter != 0) never clears.
```

### The store(0) Race — Detailed Explanation

The TTAS `lock()` protocol:

1. Spin while `load(counter) != 0`
2. `fetch_add(+1)` — attempt to acquire; returns old value
3. If old == 0: hold lock, return
4. Else: `fetch_add(-1)` to undo, spin again

With buggy `store(0)` unlock:

```text
Thread A holds lock (counter = 1)
Thread B: fetch_add(+1) -> counter=2, old=1 != 0 -> begins fetch_add(-1) undo
Thread A: store(0)          -> counter=0   [store races with B's undo]
Thread B: fetch_add(-1)     -> counter=-1  [undo lands on already-0 counter]

Now: counter = -1
Spin condition: while counter != 0  ->  True forever
DEADLOCK: no thread can advance
```

With correct `fetch_add(-1)` unlock:

```text
Thread A holds lock (counter = 1)
Thread B: fetch_add(+1) -> counter=2, old=1 -> fetch_add(-1) undo
Thread A: fetch_add(-1) -> counter=1 (or 0 if B's undo ran first)
Eventually counter reaches 0, B's inner spin exits, B retries and wins lock.
No negative counter possible.
```

The key invariant: `fetch_add` operations are sequentially consistent. Counter is
bounded below by 0 once all in-flight `fetch_add(-1)` undos have completed.

### Detailed Steps

1. **Understand the API constraint**: Mojo's `Atomic[DType.int64]` exposes only
   `fetch_add`, `fetch_sub`, `load`, `max`, and `min`. Classic CAS-based spinlocks
   (`compare_exchange_weak`) cannot be used directly. The TTAS double-check pattern works
   around this.

2. **The invariant to maintain**: The counter is exactly `1` while the lock is held
   and exactly `0` while free. `unlock()` must always subtract from 1->0. This is only
   safe if `lock()` guarantees it.

3. **Inner spin (cheap path)**: `while ptr[].load() != 0: pass` — no atomic RMW, low
   cache-line contention. Threads spend most of their time here.

4. **Atomic claim attempt**: `fetch_add(1)` atomically increments and returns the
   *previous* value. Only one thread among all concurrent `fetch_add` callers can
   observe the return value `0` (the lock was free at that instant). That thread owns
   the lock.

5. **Undo on loss**: If `fetch_add` returns `> 0`, another thread holds the lock.
   Immediately call `fetch_add(-1)` to undo the increment, then loop back. This keeps
   the counter bounded and prevents underflow in `unlock()`.

6. **Unlock with fetch_add(-1), never store(0)**: Because `lock()` only returns when
   it observes `fetch_add(+1)` return `0`, the counter is exactly `1` at that point.
   `unlock()` doing `fetch_add(-1)` always goes `1 -> 0`. Using `store(0)` instead
   is a data race that can drive the counter to -1, causing permanent deadlock.

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

8. **For CI deadlocks, check repro files**: If CI times out at 100% rate, suspect a
   spinlock deadlock before suspecting flaky infrastructure. Standalone repro files at
   `repro/spinlock_race_condition.mojo` and `repro/spinlock_deadlock.mojo` demonstrate
   BuggySpinLock (store(0)) vs CorrectSpinLock (fetch_add(-1)) side by side.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Naive fetch_add lock + fetch_sub unlock | `lock`: `fetch_add(1)` unconditionally; `unlock`: `fetch_sub(1)` | Under high contention multiple threads have in-flight increments before the holder's unlock runs. `fetch_sub(1)` goes e.g. 3->2 (not to 0), so waiting threads never see counter==0 and spin forever (liveness violation). | Counter must be exactly 1 when held, not ">=1". All contenders must undo their increment when they lose. |
| Loop in unlock: `while fetch_sub != 1` | `unlock`: keep subtracting until it returns 1 | When multiple threads have in-flight increments, looping `fetch_sub` drives the counter below 1->0->-1. The holder subtracts from a negative value; contenders see counter < 0 and either spin or underflow further. Counter never stabilizes. | The unlock path must be a single atomic operation. The cleanup of excess increments must happen in `lock()`, not `unlock()`. |
| Direct CAS translation from C++ | `compare_exchange_weak(&expected, 0, 1)` | Mojo `Atomic[DType.int64]` has no `compare_exchange_weak` or `exchange` methods (as of Mojo 0.26.x). Compilation fails. | Check Mojo Atomic API before porting. The TTAS double-check pattern is the correct Mojo substitute. |
| `store(0)` in unlock (v1.1.0 discovery) | `unlock`: `Atomic[DType.int64].store(self._lock_word(), Int64(0))` | Under TTAS contention, Thread B does `fetch_add(+1)` (gets old=1, not 0), then starts `fetch_add(-1)` undo. Thread A's `store(0)` races with B's undo: store lands first, then B's `fetch_add(-1)` goes 0->-1. Counter is now -1; spin condition `while counter != 0` is true forever. All threads deadlock. CI test group timed out at 15 min on 100% of runs. | For a TTAS lock built on `fetch_add`, unlock MUST be `fetch_add(-1)`. `store(0)` is a data race. The invariant is counter==1 when the holder calls unlock; `fetch_add(-1)` is the only correct release operation. |

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
            _ = ptr[].fetch_add(-1)  # undo: fetch_add(-1), not fetch_sub(1)

    fn unlock(mut self):
        var ptr = self._as_atomic()
        _ = ptr[].fetch_add(-1)  # CORRECT: fetch_add(-1), never store(0)
```

### Verification

```bash
# Compile and run the concurrent counter smoke test
pixi run mojo /tmp/test_lock2.mojo

# Expected output: no assertion error, exits 0
# 8 threads x 1000 iterations = exactly 8000

# For integration-level verification using real TensorMemoryPool:
pixi run mojo test tests/shared/base/test_memory_pool_threadsafe.mojo
# 8 threads x 200 iterations, all assertions must pass with no timeout
```

### Mojo Atomic API Reference (0.26.x)

| Method | Signature | Notes |
| -------- | ----------- | ------- |
| `load` | `() -> Scalar[type]` | Non-atomic on some platforms; use for cheap inner spin |
| `fetch_add` | `(rhs: Scalar[type]) -> Scalar[type]` | Returns *previous* value; atomic. Use with negative rhs for subtract. |
| `fetch_sub` | `(rhs: Scalar[type]) -> Scalar[type]` | Returns *previous* value; atomic |
| `max` | `(rhs: Scalar[type]) -> None` | Atomic max in-place |
| `min` | `(rhs: Scalar[type]) -> None` | Atomic min in-place |
| `compare_exchange_weak` | **MISSING** | Not available; use TTAS double-check pattern instead |
| `exchange` | **MISSING** | Not available |
| `store` | **MISSING in lock context** | If available, NEVER use to unlock a TTAS lock — races with in-flight undo operations |

### CI Impact Reference

| Symptom | Likely Cause | Fix |
| --------- | ------------- | ----- |
| Test group times out at 100% rate (e.g. 15 min limit) | Spinlock deadlock — all threads spinning on counter != 0 | Check `unlock()` for `store(0)` pattern; replace with `fetch_add(-1)` |
| Individual tests fail intermittently with wrong counts | Counter underflow from excess `fetch_sub` | Ensure contenders use `fetch_add(-1)` undo in `lock()`, not `fetch_sub` |
| Tests hang locally but pass in CI with fewer threads | Race only manifests under high contention | Test with `parallelize[worker](8)` to expose races |

## Verified On

| Project | Version | Context | Details |
| --------- | --------- | --------- | --------- |
| ProjectOdyssey | v1.0.0 | PR `fix/ci-stability-and-quality` — `TensorMemoryPool` SpinLock race causing 6 thread-safety test failures | Compiled and ran 8-thread x 1000-iteration counter test locally with `pixi run mojo`; CI auto-merge enabled |
| ProjectOdyssey | v1.1.0 | Branch `ci-main-green` — `store(0)` unlock race in TTAS protocol causing Core Utilities C test group to time out at 15 min on 100% of CI runs | Fix: replaced `store(0)` with `fetch_add(-1)` in `SpinLock.unlock()`; pushed to CI; run in progress |
