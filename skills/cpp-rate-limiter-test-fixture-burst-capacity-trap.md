---
name: cpp-rate-limiter-test-fixture-burst-capacity-trap
description: "Token-bucket RateLimiter constructor takes (tokens_per_sec, burst_capacity) not (max_requests, window). Tests that pass burst_capacity=1e9 will never see 429. Use when: (1) writing a test that exercises rate-limit exceedance, (2) a RateLimit test passes locally but the production limiter mysteriously never fires, (3) inheriting a token-bucket library and not sure what the second constructor arg means."
category: testing
date: 2026-05-17
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [rate-limiter, token-bucket, test-fixture, burst-capacity, cpp, agamemnon, httplib, route-test]
---

# C++ Rate Limiter Test Fixture: burst_capacity Trap

## Overview

| Field | Value |
| --- | --- |
| Date | 2026-05-17 |
| Objective | Capture the `burst_capacity` vs `window_ns` constructor-argument confusion in token-bucket rate limiters |
| Outcome | Test fix: `RateLimiter{2, 1e9}` -> `RateLimiter{2, 2}` |
| Verification | verified-ci |

## When to Use

1. Writing a test that exercises rate-limit exceedance (expects HTTP 429 / `allow()` returning false after N calls).
2. A `RateLimit` test passes locally but the production limiter mysteriously never fires.
3. Inheriting a token-bucket library and unsure what the second constructor argument means.

## Verified Workflow / Quick Reference

```bash
# Before writing a rate-limit test: check the constructor signature
grep -n "RateLimiter[^(]*([^)]*)" include/projectagamemnon/rate_limiter.hpp
# Confirm it's (tokens_per_sec, burst_capacity) not (max_requests, window_ns)
# Then for a test that expects N requests/window to be allowed: pass burst_capacity = N
```

```cpp
RateLimiter rate_limiter_{2, 2};   // CORRECT - 2 tokens/sec rate, 2-token burst
RateLimiter rate_limiter_{2, 1e9}; // WRONG   - burst of 1 billion tokens, never fires
```

## Verified Workflow / Detailed Steps

1. **Read the production wiring first.** In ProjectAgamemnon `src/routes.cpp`,
   `set_pre_routing_handler` invokes `rl->allow(req.remote_addr)` for every
   non-exempt path. Exempt paths: `/health`, `/v1/health`, `/v1/version`.
2. **Understand the bucket model.** The limiter maintains one token bucket per
   remote IP. Tokens refill at `tokens_per_second` and the bucket holds at most
   `burst_capacity` tokens. A request consumes one token; if the bucket is
   empty, `allow()` returns false and the handler emits HTTP 429 with
   `Retry-After: ceil(1.0 / tokens_per_second)` seconds.
3. **Pick `burst_capacity = N`** where N is the intended request budget the
   test will burn through before expecting a 429. If you want "3 requests then
   429", construct `RateLimiter{tokens_per_sec, 3}`.
4. **Target a non-exempt path** in the test (`/v1/teams`, not `/health`),
   otherwise the limiter is bypassed entirely regardless of bucket config.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| 1 | Treated second constructor arg as a window in nanoseconds; passed `1e9` thinking "1 second window" | Actual semantics is `burst_capacity` (token count). The bucket held 1 billion tokens, so `allow()` always returned true and the test never observed a 429. | Read the constructor decl/doc before guessing units. Numeric literals like `1e9` are a red flag — units must be confirmed at the source. |
| 2 | Switched test target from `/health` to `/v1/teams` without fixing burst | Exempt-path bypass was real, but burst was still `1e9` so the limiter still never engaged on the new path either. | Two independent bugs can hide each other. Investigate the limiter config BEFORE assuming the exempt-path hypothesis alone is sufficient. |

## Results & Parameters

- **Production wiring location:** `src/routes.cpp`, `set_pre_routing_handler`
  calls `rl->allow(req.remote_addr)` for non-exempt paths.
- **Exempt paths:** `/health`, `/v1/health`, `/v1/version`.
- **Burst formula for "N requests per window" test:** `burst_capacity = N`.
- **Retry-After header formula:** `ceil(1.0 / tokens_per_second)` seconds.
- **Bucket scope:** one bucket per `req.remote_addr` (per-IP, not global).

## Verified On

- Repository: ProjectAgamemnon
- Session: 2026-05-17
- PR: #393 (fix-ci circuit breaker; `RateLimitedRouteTest` fixture corrected)
