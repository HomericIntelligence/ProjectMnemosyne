---
name: mojo-parallelize-worker-stash-parity-testing
description: "Mojo 1.0.0b1 std.algorithm.parallelize patterns: workers cannot raise (stash-and-re-raise via pre-sized per-worker slots), perf_counter_ns timing (time.now() does not exist), field-level-disjointness safety argument for shared mut struct captures, and the CI test triad that makes parallel updates defensible (bit-exact parallel-vs-serial parity, exact interval-sweep concurrency-achievement, worker-error stash isolation). Use when: (1) parallelizing per-layer or per-shard work in Mojo with parallelize/sync_parallelize, (2) a worker closure hits a compile error because it raises, (3) proving parallel and serial training paths are bit-identical, (4) measuring whether parallelize actually ran concurrently instead of silently degrading to sequential, (5) computing max simultaneous overlap from timestamped intervals without the naive overlap-counting overcount."
category: testing
date: 2026-07-10
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - mojo
  - parallelize
  - concurrency
  - error-handling
  - parity-testing
  - perf-counter
  - interval-sweep
  - data-race
---

# Mojo parallelize: Worker Error Stashing, Timing, and Parity Testing

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-10 |
| **Objective** | Ship `std.algorithm.parallelize`-based per-layer parallel training updates in Mojo 1.0.0b1 with all patterns unit-tested and green in CI |
| **Outcome** | Successful — parallel per-layer updates landed with bit-exact serial parity, verified concurrency achievement, and isolated worker-error handling |
| **Verification** | verified-ci |

## When to Use

- Parallelizing per-layer, per-shard, or per-partition work in Mojo via `std.algorithm.parallelize` / `sync_parallelize`
- A `parallelize` worker closure fails to compile because it raises (any fn/def closure spelling)
- You need to propagate errors out of parallel workers that cannot raise
- You need timestamps inside Mojo 1.0.0b1 (and `from std.time import now` fails to compile)
- Proving a parallel code path is bit-identical to its serial counterpart (e.g., parallel vs serial optimizer steps)
- Verifying that `parallelize` actually ran workers concurrently rather than silently degrading to sequential execution
- Computing max simultaneous overlap from recorded start/end timestamps (exact concurrency metric)
- Arguing safety for multiple workers sharing one `mut` struct capture

## Verified Workflow

### Quick Reference

```mojo
# 1. Workers CANNOT raise in Mojo 1.0.0b1 — stash-and-re-raise pattern:
var errors = List[String]()
for _ in range(num_workers):
    errors.append("")          # PRE-SIZE distinct slots BEFORE parallelize

@parameter
fn worker(l: Int):             # must not raise — compile error otherwise
    try:
        update_layer(model, l)
    except e:
        errors[l] = String(e)  # distinct index per worker — never append from workers

parallelize[worker](num_workers)

for l in range(num_workers):   # orchestrator re-raises after the join
    if len(errors[l]) > 0:
        raise Error(errors[l])
```

```mojo
# 2. Timing in 1.0.0b1: time.now() does NOT exist. Use perf_counter_ns (nanoseconds, monotonic):
from std.time import perf_counter_ns
var t0 = perf_counter_ns()   # process-wide — cross-worker timestamps directly comparable
```

```mojo
# 3. Exact max-simultaneous-concurrency from [start, end) intervals — sweep START points only:
fn max_concurrency(starts: List[Int], ends: List[Int]) -> Int:
    var best = 0
    for i in range(len(starts)):
        var p = starts[i]
        var count = 0
        for j in range(len(starts)):
            if starts[j] <= p and ends[j] > p:   # excludes zero-duration intervals correctly
                count += 1
        if count > best:
            best = count
    return best
```

### Detailed Steps

1. **Worker error handling — stash-and-re-raise (mandatory).**
   `parallelize[worker](N)` workers cannot raise in Mojo 1.0.0b1; it is a compile error regardless of fn/def closure spelling. The stdlib `sync_parallelize` docstring states exceptions "cause a trap rather than be propagated." Pattern:
   - Pre-size a `List[String]` with one slot per worker **before** dispatch.
   - Each worker catches internally and writes its error into its own distinct index. **Never `append` to a shared List from workers — that is a data race** (List growth mutates shared length/capacity).
   - After the `parallelize` join, the orchestrator scans all slots and re-raises the first (or aggregated) non-empty error.
   - A worker **trap** (e.g., segfault — not a raise) aborts the whole process; no supervisor exists. Document this as accepted behavior in the module docstring.

2. **Timing.** `time.now()` does not exist in 1.0.0b1 (`from std.time import now` is a compile error). Use `std.time.perf_counter_ns`: monotonic, **nanoseconds** (validate empirically — timing a `sleep(0.25)` measured ~250,258,897 counts), and process-wide, so timestamps recorded by different workers are directly comparable.

3. **Concurrency-safety argument for shared `mut` model capture.** `@parameter` closures capture by reference; multiple workers share one `mut` model struct. Safety comes from **field-level disjointness**: worker `l` touches only layer `l`'s tensors, optimizer state, and stash/timing slots. Two traps to cover explicitly:
   - Refcounted shared-ownership tensor types: assignment bumps a refcount, so the safety argument must cover the **read side** too — verify no tensor is refcount-bumped from two workers (e.g., a staging step that copy-assigns a shared tensor).
   - The compiler does **not** enforce any of this. State the full disjointness argument in the docstring of the parallel-update function.

4. **Test triad (all in CI) that makes the parallel path defensible:**
   - **Bit-exact parallel-vs-serial parity:** construct two identically-seeded model copies, step one through the parallel path and one through the serial path, compare **all** parameter tensors element-wise with `atol=0.0` plus exact loss equality. Run it **20x with varying deterministic batches** as a stress test — a single lucky execution cannot bound a race.
   - **Concurrency-achievement test:** N=4 workers each busy-wait ≥50 ms, recording `perf_counter_ns` start/end into disjoint slots; compute max simultaneous overlap via the exact interval sweep and **assert ≥2, not ==4** (flake-safe on contended CI runners; log the observed value — typically 4/4). Without this test, nothing catches `parallelize` silently degrading to sequential.
   - **Worker-error stash test:** 4 workers with one deliberately failing; assert the failing slot is isolated (correct index, correct message) and the other workers complete.

5. **Exact concurrency metric — sweep interval START points only.** Concurrency over time is a step function that only increases at interval starts, so evaluating the overlap count at every start point is exact. The naive "count intervals overlapping a witness interval" approach **overcounts**: with A=[0,10], B=[0,3], C=[5,8], both B and C overlap A but never coexist — naive says 3, truth is 2. The predicate `start_j <= p and end_j > p` also correctly excludes zero-duration intervals.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Raising from a `parallelize` worker | Worker closure declared as raising (tried both fn and def closure spellings) | Compile error in Mojo 1.0.0b1 — workers cannot raise; stdlib `sync_parallelize` docstring says exceptions "cause a trap rather than be propagated" | Use stash-and-re-raise: catch inside the worker, write the error String into a pre-sized per-worker slot, re-raise from the orchestrator after the join |
| Workers `append`ing errors to a shared `List[String]` | Collect worker errors by appending to one shared list | Data race — `append` mutates shared length/capacity from multiple threads | Pre-size the list before dispatch; each worker writes only its own distinct index |
| `from std.time import now` / `time.now()` | Standard-library timer name from older Mojo docs | `time.now()` does not exist in 1.0.0b1 — compile error | Use `std.time.perf_counter_ns` (monotonic, nanoseconds, process-wide); validate the unit empirically (sleep(0.25) ≈ 250,258,897 counts) |
| Naive overlap counting for the concurrency metric | Count how many intervals overlap a witness interval | Overcounts: A=[0,10], B=[0,3], C=[5,8] — B and C both overlap A but never coexist (naive says 3, truth is 2) | Sweep over interval START points only (concurrency only increases at starts — exact); predicate `start_j <= p and end_j > p` excludes zero-duration intervals |
| Single parity run as the race check | One parallel-vs-serial comparison | A single lucky execution cannot bound a race | Run the bit-exact parity check 20x with varying deterministic batches as a stress test |
| Asserting full overlap (==4) in the concurrency test | Require all 4 workers simultaneously overlapping | Flaky on contended CI runners | Assert ≥2 and log the observed value (typically 4/4) |

## Results & Parameters

**Measured outcomes (8 parallel per-layer updates on an 8-thread CPU, CI-green):**

| Metric | Value |
|--------|-------|
| Step concurrency | 1.0 (all 8 layer-update workers overlap) |
| Update-phase speedup | ~3.5x, ≈ sum/max — bounded by the heaviest layer |
| Per-worker wall-clock instrumentation overhead | <0.01% per step |
| `perf_counter_ns` unit validation | sleep(0.25) measured ≈ 250,258,897 counts (nanoseconds confirmed) |

**Test parameters that shipped:**

- Parity: all parameter tensors element-wise, `atol=0.0`, exact loss equality, 20 repetitions with varying deterministic batches
- Concurrency-achievement: N=4 workers, busy-wait ≥50 ms each, assert max overlap ≥2 (log observed)
- Error-stash: 4 workers, 1 deliberate failure, assert slot isolation + sibling completion

**Accepted behavior to document:** a worker trap (segfault, not raise) aborts the whole process — no supervisor exists in `parallelize`.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| predictive-coding-mojo | PC-12B + PC-12 — per-layer parallel training updates via `std.algorithm.parallelize`, Mojo 1.0.0b1, all patterns unit-tested and CI-green | verified-ci |
