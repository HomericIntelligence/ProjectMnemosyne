---
name: testing-gtest-skip-inside-helper-keeps-test-running
description: "GTEST_SKIP() called inside a helper/fixture method only aborts THAT function (it uses the fatal-assertion mechanism), so the test is marked skipped but the TEST body keeps executing every statement after the helper returns. Use when: (1) you factor an env-var/precondition skip into a fixture helper like require_X() and call it from test bodies, (2) a test reports SKIPPED yet its side effects (docker commands, file writes, crashes) still happen, (3) a 'skipped' test dies with std::logic_error/segfault from std::string(nullptr) built from an unset getenv, or with std::terminate because an exception unwound through a throwing RAII guard, (4) reviewing gtest code where GTEST_SKIP/ASSERT_* live in non-void helpers or subroutines. Fix: inline GTEST_SKIP() directly in the TEST body, or follow every possibly-skipping helper call with `if (::testing::Test::IsSkipped()) return;`. Same rule applies to ASSERT_* in helpers (gtest docs: fatal assertions abort only the current function)."
category: testing
date: 2026-07-03
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [gtest, gtest-skip, skip-semantics, fixture-helper, fatal-assertion, undefined-behavior, std-terminate, raii-guard, getenv-null, integration-tests, code-review]
---

# Testing: GTEST_SKIP Inside a Helper Keeps the Test Body Running

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-03 |
| **Objective** | Gate broker-bounce integration tests on an optional env var (`NESTOR_LIVE_NATS_COMPOSE`) via a fixture helper `require_compose_ctl()` that called `GTEST_SKIP()` |
| **Outcome** | Trap identified in PR review and fixed: `GTEST_SKIP()` in the helper marked the test skipped but the test body continued, reaching `std::string(nullptr)` UB and a `std::terminate` path. Fix = inline the skip check into each test body. Fix verified locally (suite green in both env configurations) |
| **Verification** | verified-local — fixed suite compiled and ran green locally (8/8 with broker; 6 pass + 2 skip with the compose var unset); CI validation pending on ProjectNestor PR #120 |

## When to Use

- You are about to factor a skip condition (env var, tool availability, platform check) into a gtest fixture helper (`void require_X()`) called from test bodies.
- A test reports `SKIPPED` in the ctest/gtest summary, yet its side effects still occur (processes spawned, files written, docker commands run) — classic signature of skip-in-helper.
- A "skipped" test crashes: `std::logic_error` (libstdc++) or segfault (libc++) from constructing `std::string` out of a null `getenv()` result, or `std::terminate` with no test failure output.
- Code review of any gtest suite where `GTEST_SKIP()` or `ASSERT_*` appear in helper functions/subroutines rather than directly in `TEST`/`TEST_F` bodies.

## Verified Workflow

### Quick Reference

```cpp
// BROKEN — skip only aborts require_compose_ctl(), not the caller:
void require_compose_ctl() {
  if (compose_file() == nullptr) {
    GTEST_SKIP() << "NESTOR_LIVE_NATS_COMPOSE not set";
  }
}
TEST_F(LiveTest, Bounce) {
  require_compose_ctl();      // test now marked skipped...
  compose_ctl("stop");        // ...but THIS STILL RUNS -> std::string(nullptr) UB
}

// FIX A (preferred) — inline the skip so it aborts the test body itself:
TEST_F(LiveTest, Bounce) {
  if (compose_file() == nullptr) {
    GTEST_SKIP() << "NESTOR_LIVE_NATS_COMPOSE not set";
  }
  ...
}

// FIX B — keep the helper but guard after every call:
require_compose_ctl();
if (::testing::Test::IsSkipped()) return;
```

### Detailed Steps

1. **Know the mechanism.** `GTEST_SKIP()` is implemented like a fatal assertion: it records the skip result and `return`s from the CURRENT function. It cannot unwind the caller. (Same long-documented gtest rule as "ASSERT_* in a subroutine does not abort the test".)
2. **Trace what runs after a helper-skip.** In the ProjectNestor live-NATS suite, `require_compose_ctl()` skipping meant the bounce test body still ran `compose_ctl("stop")`, which built `std::string` from a null `getenv()` result — `std::logic_error` on libstdc++, segfault on libc++.
3. **Watch for the double-fault escalation.** In the second bounce test the throw from `compose_ctl` unwound past an RAII `BrokerRestoreGuard` whose destructor itself ran a failing command path that could throw — throwing during unwinding calls `std::terminate` and kills the whole test binary, taking every remaining test with it.
4. **Fix by inlining.** Move `if (precondition_missing) GTEST_SKIP() << ...;` to the top of each `TEST_F` body. This is mechanical and reviewable; helpers keep only pure queries (`compose_file()`).
5. **Defense in depth.** Also null-guard the downstream helper (`const char* f = compose_file(); if (f == nullptr) { ADD_FAILURE() << "..."; return false; }`) so any future misuse fails with a readable message instead of UB.
6. **Verify BOTH configurations.** Run the suite once with the optional env var set (all tests execute) and once with it unset (gated tests report `Skipped`, binary exits cleanly). The unset run is the regression test for this trap.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| GTEST_SKIP in a fixture helper | `void require_compose_ctl() { if (!env) GTEST_SKIP(); }` called at top of bounce tests | GTEST_SKIP only aborts the current function; test was marked skipped but the body kept executing into `std::string(nullptr)` UB, and in one test the throw unwound through a throwing RAII guard destructor → `std::terminate` | Skip/fatal-assert macros must execute in the TEST body itself, or every helper call must be followed by an `IsSkipped()` check |
| Relying on the skip mark as a safety gate | Assumed "test shows SKIPPED" implies "test code did not run" | The skip RESULT and the control FLOW are independent when the macro runs in a callee | Treat a SKIPPED test that still produced side effects as this bug until proven otherwise |
| Leaving the null-deref reachable after fixing call sites | Only fixing the two call sites, keeping `compose_ctl` unguarded | Any future caller reintroduces UB silently | Add the null guard in the shared helper too (`ADD_FAILURE` + `return false`) — readable failure beats UB |

## Results & Parameters

| Parameter | Verified Value |
|-----------|----------------|
| Failing pattern | `GTEST_SKIP()` inside fixture method called from `TEST_F` body |
| Symptom A | Test reports SKIPPED but side effects still execute |
| Symptom B | `std::logic_error` (libstdc++) / segfault (libc++) from `std::string(getenv(...))` with var unset |
| Symptom C | `std::terminate` when the resulting throw unwinds through a throwing RAII destructor |
| Fix applied | Inline `if (compose_file() == nullptr) GTEST_SKIP() << ...;` at top of each gated `TEST_F`; helper deleted |
| Alternative fix | `helper(); if (::testing::Test::IsSkipped()) return;` |
| Hardening | Null guard in shared helper: `ADD_FAILURE() << "compose_ctl called without NESTOR_LIVE_NATS_COMPOSE set"; return false;` |
| Regression check | Run suite with gating var unset: gated tests `Skipped`, zero failures, clean exit |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectNestor | PR #120 (issue #119) live-NATS integration suite, review thread fixes | Fix ran green locally: 8/8 with broker + compose var; 6 pass / 2 skip with compose var unset; CI pending |
