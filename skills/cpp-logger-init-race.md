---
name: cpp-logger-init-race
description: "A SIGABRT / 'Subprocess aborted' that appears only under -O0 --coverage (or TSan) builds, with a CI log line like `terminate called after throwing an instance of 'spdlog::spdlog_ex'  what(): logger with name '<name>' already exists`, is a check-then-act data race in a lazy logger singleton — NOT a flaky assertion. Use when: (1) a unit test intermittently aborts (SIGABRT) only in coverage/TSan CI builds, (2) CI logs show spdlog_ex / 'already exists' / 'terminate called', (3) a prior PR relaxed an assertion tolerance to 'fix flakiness' but the abort persisted, (4) any lazily-initialized C++ singleton (logger, registry) is created from multiple threads without synchronization."
category: debugging
date: 2026-05-29
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - cpp
  - thread-safety
  - data-race
  - check-then-act
  - spdlog
  - lazy-singleton
  - sigabrt
  - coverage-build
  - tsan
  - call-once
  - flaky-test-fallacy
---

# C++ Lazy Logger Init Race — Check-Then-Act SIGABRT in Coverage Builds

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-29 |
| **Objective** | Diagnose and permanently fix an intermittent unit-test SIGABRT that only reproduced under the `-O0 --coverage` CI build, after an earlier PR had mis-treated it as a flaky assertion |
| **Outcome** | Success — root-caused as a check-then-act data race in a lazy `spdlog` named-logger singleton; fixed with a function-local mutex + `spdlog::get` reuse. Merged via PR #576; CI passed on main |
| **Verification** | verified-ci |

## When to Use

- A unit test **intermittently aborts** (`SIGABRT` / "Subprocess aborted") and the failure appears **only** under the `-O0 --coverage` build (and likely under TSan), not in normal Debug/Release.
- CI logs contain `terminate called after throwing an instance of 'spdlog::spdlog_ex'` and/or `what(): logger with name '<name>' already exists`.
- A previous PR "fixed flakiness" by **relaxing an assertion tolerance** (e.g., widening `EXPECT_LE`/`EXPECT_NEAR` bounds) but the abort kept happening.
- Any C++ code that **lazily initializes a singleton** (logger, registry, cache) from multiple threads via an unsynchronized `if (!ptr) ptr = create();` pattern.
- You are tempted to re-run a "flaky" job — STOP and read this first.

## Verified Workflow

### Quick Reference

```bash
# 1. Do NOT grep for the assertion text. Grep for the CRASH signature:
grep -nE "terminate called|spdlog_ex|already exists|Subprocess aborted|SIGABRT" ci-log.txt

# 2. Reproduce deterministically with the coverage build (widest race window):
cmake --preset coverage && cmake --build --preset coverage
ctest --preset coverage -R BackpressureConcurrentTrigger --output-on-failure --repeat until-fail:50

# 3. Fix: guard the lazy init with a function-local mutex + reuse already-registered logger.
```

### Detailed Steps

1. **Classify the failure correctly.** An `EXPECT_*`/`ASSERT_*` failure marks a test
   FAILED but does **not** abort the subprocess. A `SIGABRT` / "Subprocess aborted" /
   "terminate called" means a **crash or uncaught exception** on some thread. These are
   fundamentally different. If you see an abort, the assertion was never the cause.
2. **Grep the CI log for the crash signature**, not the test name or assertion text:
   `terminate|spdlog_ex|already exists|Subprocess aborted|SIGABRT`. The tell here is:
   `terminate called after throwing an instance of 'spdlog::spdlog_ex'  what(): logger with name '<name>' already exists`.
3. **Locate the lazy logger init.** Search for `stdout_color_mt`, `spdlog::*_mt(`, or a
   `if (!logger_)` guard. `spdlog::stdout_color_mt(name)` (and the other `_mt` factories)
   **throw `spdlog_ex` if a logger with that name is already registered** in spdlog's
   global registry.
4. **Confirm it is check-then-act.** Two threads both evaluate `if (!logger_)` as true,
   both call `stdout_color_mt("keystone")`; the second registration throws. The throw is
   on a worker thread, uncaught → `std::terminate()` → abort. `-O0 --coverage` widens the
   window (extra instrumentation between the check and the act) enough to reproduce nearly
   every run.
5. **Fix with a function-local mutex (Meyers-singleton mutex) AND defensive reuse:**
   - Serialize `init()`/`shutdown()` so the named logger is created exactly once.
   - Before calling `stdout_color_mt(name)`, check `spdlog::get(name)` and reuse it if
     present, so an `init() → shutdown() → init()` cycle (or any leftover registration)
     can never throw.
6. **Verify with repeat-until-fail under the coverage build** (`ctest --repeat until-fail:N`),
   then let CI confirm on the `-O0 --coverage` job. Only then claim it fixed.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Relax the test assertion tolerance (PR #559) | Widened the test's `EXPECT_LE`/tolerance bounds, assuming a flaky numeric assertion | The failure was a `terminate()`/SIGABRT, not an assertion failure. Loosening assertion bounds cannot stop a process from crashing — the abort persisted unchanged | An aborted subprocess is **never** a flaky assertion. A failing `EXPECT/ASSERT` marks the test failed but keeps the process alive; an abort means a crash or uncaught exception. Find the crash, don't tune the assertion |
| Re-run the job hoping it's transient | Re-triggered the CI job assuming infra/flaky noise | Deterministic under the `-O0 --coverage` build — re-running reproduced the same abort | "There is no such thing as a flaky test; the test needs to be fixed." Determinism under a coverage/TSan build is a signal of a real data race, not infra noise. (This is the case where the assume-flaky / `retrigger-flaky-ci` reflex is WRONG.) |

## Results & Parameters

**Symptom (CI log, the diagnostic tell):**

```text
terminate called after throwing an instance of 'spdlog::spdlog_ex'
  what():  logger with name 'keystone' already exists
[  FAILED  ] AgentCoreTest.BackpressureConcurrentTrigger (Subprocess aborted)
```

**Before — unsynchronized check-then-act (racy, aborts under concurrency):**

```cpp
// Logger::log() — first caller lazily initializes
void Logger::log(/* ... */) {
    if (!logger_) {        // THREAD A and THREAD B both see null
        init();
    }
    // ... use logger_ ...
}

void Logger::init() {
    if (!logger_) {        // both pass the check
        // both call the factory; the SECOND throws spdlog_ex:
        //   "logger with name 'keystone' already exists"
        logger_ = spdlog::stdout_color_mt("keystone");
    }
}
```

**After — function-local mutex (created exactly once) + `spdlog::get` reuse (never throws):**

```cpp
namespace {
// Meyers-singleton mutex: one shared, thread-safe-initialized mutex.
std::mutex& init_mutex() {
    static std::mutex m;
    return m;
}
}  // namespace

void Logger::init() {
    std::lock_guard<std::mutex> lock(init_mutex());
    if (logger_) {
        return;  // already initialized for this Logger
    }
    // Defensive: if the named logger is already in spdlog's global registry
    // (e.g. after an init()/shutdown()/init() cycle), reuse it instead of
    // re-registering — stdout_color_mt() would otherwise throw spdlog_ex.
    if (auto existing = spdlog::get("keystone")) {
        logger_ = existing;
    } else {
        logger_ = spdlog::stdout_color_mt("keystone");
    }
}

void Logger::shutdown() {
    std::lock_guard<std::mutex> lock(init_mutex());
    if (logger_) {
        spdlog::drop("keystone");  // unregister so a later init() is clean
        logger_.reset();
    }
}
```

**Generalization:**

- `spdlog::stdout_color_mt(name)` (and the other named `*_mt` factories) **throw
  `spdlog::spdlog_ex` if `name` is already registered** in spdlog's process-global
  registry. Any lazily-created spdlog named logger reachable from multiple threads is
  vulnerable.
- This is the generic **check-then-act lazy-singleton race** in C++. Fix options, in
  order of preference:
  1. `std::call_once` + `std::once_flag` (cleanest for "init exactly once").
  2. A function-local (`static`) `std::mutex` guarding init/shutdown.
  3. Register the singleton **once at startup**, before any threads spin up, avoiding
     lazy init entirely.
- Always reproduce thread-safety fixes under the **widest-window build** available
  (`-O0 --coverage` or TSan) with `ctest --repeat until-fail:N` before declaring victory.

**Build that reproduces deterministically:** `-O0 --coverage` (coverage instrumentation
widens the check→act gap). TSan would also flag the data race directly.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectKeystone | 2026-05-29 — `AgentCoreTest.BackpressureConcurrentTrigger` aborted only under `-O0 --coverage`. Root-caused after PR #559 mis-treated it as a flaky assertion (tolerance relaxed, abort persisted). Fixed in PR #576 (function-local mutex + `spdlog::get` reuse); CI passed on main. | spdlog named-logger `"keystone"` lazy init race |
