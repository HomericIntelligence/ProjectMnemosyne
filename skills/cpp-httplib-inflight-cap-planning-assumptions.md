---
name: cpp-httplib-inflight-cap-planning-assumptions
description: "Use when planning (not yet implementing) a global in-flight request cap / backpressure / concurrency throttle for a cpp-httplib (or similar embedded HTTP) server, or when reviewing such a plan, or for any design that must release a per-request resource on every exit path. PRIMARY learning: when a framework offers only two SEPARATE lifecycle callbacks (pre/post-routing), do NOT split acquire/release across them — DECORATE each handler with a closure that constructs an RAII guard at handler entry so it destructs on every exit (normal/early/throw), removing the unverifiable post-routing-fires-on-every-path assumption. Also captures: verify call-site COUNTS by fresh grep before asserting them in a plan, std::counting_semaphore availability, and the default-cap heuristic."
category: architecture
date: 2026-06-20
version: "1.1.0"
verification: unverified
user-invocable: false
history: cpp-httplib-inflight-cap-planning-assumptions.history
tags: []
---

# C++ cpp-httplib Global In-Flight Request Cap: Planning Assumptions Skill

**History:** [changelog](./cpp-httplib-inflight-cap-planning-assumptions.history)

## Overview

| Field | Value |
| --- | --- |
| Date | 2026-06-20 |
| Objective | Capture the durable lessons for planning/reviewing a global in-flight request cap (backpressure throttle) on a cpp-httplib server, and the design pivot that resolves them: bind the per-request resource to each handler's own scope via a decorating RAII wrapper, instead of splitting acquire/release across pre/post-routing callbacks |
| Outcome | Re-plan produced (planning artifact only — no code written, built, or run). **The original #1 risk (post-routing-fires-on-every-exit-path) was RESOLVED by the handler-wrapper pivot: the design no longer depends on post-routing lifecycle at all.** |
| Verification | unverified |
| History | [changelog](./cpp-httplib-inflight-cap-planning-assumptions.history) — amended v1.0.0 → v1.1.0 after R0 NOGO |
| Context | ProjectAgamemnon issue #273 — add a global in-flight request cap to the cpp-httplib HTTP server, rejecting over-cap requests with 503. R1 re-plan after R0 received a NOGO for the split-callback risk this skill itself flagged |

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms. The re-plan was never built or run; the design and parameters below are asserted from convention and a fresh code read, and remain unverified against a running binary.

## When to Use

1. Planning request throttling, backpressure, or a global in-flight concurrency cap for a cpp-httplib or other embedded HTTP server.
2. Reviewing such a plan — use the lessons below as the reviewer checklist. The #1 focus is now whether the design binds the resource to a single scope (RAII), not whether a split-callback lifecycle was "verified."
3. Planning or reviewing **any per-request resource cap on a cpp-httplib (or similar two-callback) HTTP server** where a resource (semaphore slot, lock, buffer) must be released on every exit path.
4. **A design splits acquire/release across pre/post-routing callbacks** (or any two separate lifecycle hooks) — flag it and propose the per-handler RAII wrapper instead.
5. **Adding a parameter to a widely-called registration function** (e.g. `register_routes`) — verify the call-site COUNT by a fresh grep before asserting it in a plan.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms. The section is titled "Verified Workflow" only because the repository validator (`scripts/validate_plugins.py`) requires that literal heading; the `verification: unverified` frontmatter is authoritative — this is a planning artifact and the re-plan was never built or run.

The design under review (R1): cap concurrent in-flight requests by decorating each throttled route handler with an RAII-guard closure; reject over-cap requests with `503 + Retry-After: 1`; cap is env-configurable (`MAX_INFLIGHT_REQUESTS`, default 64, `0` = disabled). The R0 design (acquire in pre-routing / release in post-routing) was abandoned because its correctness depended on the unverifiable guarantee that the post-routing callback fires on every abnormal exit.

### Quick Reference

**1. Handler-wrapper RAII recipe (the PRIMARY learning).** When a per-request resource must be released on EVERY exit path but the framework only offers two SEPARATE lifecycle callbacks, do NOT acquire in one and release in the other. Instead decorate each route handler with a closure that constructs an RAII guard at handler entry; the guard destructs at handler exit — on normal return, early return, AND exception — with ZERO assumptions about the routing lifecycle:

```cpp
static httplib::Server::Handler with_resource_cap(Limiter* lim, httplib::Server::Handler h) {
  return [lim, h = std::move(h)](const httplib::Request& req, httplib::Response& res) {
    ResourceGuard guard(*lim);              // acquire (single scope)
    if (!guard.held()) {                    // pool exhausted
      res.status = 503;
      res.set_header("Retry-After", "1");
      res.set_content(R"({"error":"server at capacity"})", "application/json");
      return;                               // guard not held -> releases nothing
    }
    h(req, res);                            // released on ANY exit of this scope
  };
}
```

- Capture `[lim, h = std::move(h)]` **BY VALUE**. cpp-httplib copies handlers into `std::function`; a by-ref / `[&]` capture dangles (the project's canonical capture-UB rule).
- Apply the wrapper **only to throttled routes**. Exempt routes (health/version/metrics) are simply never wrapped — **NO hand-maintained `!exempt && !rejected` exclusion list** (the R0 split design needed one, and it silently breaks when a future early-return status is added).
- The guard must be the **PRODUCTION mechanism**, not a test-only helper. R0 built an RAII guard then bypassed it on the live path (a YAGNI / dead-code smell a reviewer flags under SRP). Use the guard ON the production path.

**2. Fresh-grep the call-site COUNT before asserting it (the SECONDARY learning).** When adding a parameter to a widely-called function, the grep is the source of truth — count it THIS session, list every site, and rely on the whole-tree compile as the safety net (a missed site is a compile error, not a silent gap):

```bash
# Count + list EVERY call site this session; do not trust memory or stale comments.
# (R0 claimed 3 sites — "ALL THREE files"; a fresh grep found 9 across 8 files.)
grep -rn "register_routes(" src test | grep -v "/.claude/"   # exclude worktrees
```

Stale in-code comments (e.g. "ALL THREE files must be updated") are themselves drift to fix when the real count changes.

**3. Boundary translation + observability (TERTIARY).** Translate the low-level "no slot" condition into a domain HTTP response (`503` + `Retry-After`) at the boundary rather than leaking the primitive (resilience / circuit-breaker error translation). Make the rejection explicit/observable (status + header), not a silent drop (boundary observability). The shared slot counter's thread-safety rides on the semaphore's internal atomics (or a mutex fallback) — no app-level shared mutable state exposed.

**4. Toolchain + default checks still required.** Confirm `<semaphore>` is present (C++20 target ≠ `<semaphore>` guaranteed — add a build-time compile check; provide a `std::mutex`+counter fallback behind the same API), and load-test the default cap (64 is a starting heuristic; a 1 MB body can expand to several MB of parsed JSON):

```bash
echo '#include <semaphore>
int main(){ std::counting_semaphore<1<<20> s{64}; return s.try_acquire()?0:1; }' \
  | ${CXX:-c++} -std=c++20 -x c++ - -o /tmp/sem_check && /tmp/sem_check; echo "exit=$?"
```

What was SOUND across both plans (kept for balance — do not relitigate these):

- Reuse the existing raw-pointer-by-value capture convention (limiter owned by `main()`, captured by pointer) rather than inventing a new lifetime model.
- Reject (503) with non-blocking `try_acquire()` instead of blocking on the fixed-size HTTP thread pool — blocking would deadlock the very threads being protected.
- Make the cap optional (`0` = disabled) so existing tests and the shared fixture are unaffected.
- Acquire the slot LAST (inside the throttled handler, after auth + rate-limit run) so cheap rejections do not consume capacity.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Split acquire/release across pre/post-routing callbacks | Acquire a slot in `set_pre_routing_handler`, release it in `set_post_routing_handler`, guarded by a hand-written `release iff (!exempt && !rejected)` complement | Correctness depended on the unverifiable guarantee that the post callback fires on EVERY abnormal exit (read/write timeout, client disconnect, transport-layer 413 from `set_payload_max_length`). If it doesn't fire, the slot leaks until capacity reaches zero — a self-inflicted DoS, worse than the bug being fixed. R0 was NOGO'd for exactly this. | Bind the per-request resource to the handler's OWN scope via a decorating RAII wrapper; the destructor runs on normal return, early return, and exception with zero routing-lifecycle assumptions. |
| Build an RAII guard but bypass it on the live path | R0 built a `ResourceGuard` RAII type but used the split pre/post callbacks on the production path, with the guard reserved for tests, plus a hand-maintained complement condition | Dead code on the production path (YAGNI / SRP smell a reviewer flags) and the complement invariant silently breaks when a future early-return status is added. | Use the guard ON the production path (it IS the mechanism). Exempt routes are simply never wrapped — no exclusion list to keep in sync. |
| Assert call-site count from memory / a stale comment | R0 claimed `register_routes` had 3 call sites ("ALL THREE files"), echoing an in-code comment | A fresh `grep -rn "register_routes(" src test` (excluding `.claude/` worktrees) found 9 invocations across 8 files (two in one file). An undercount of a mechanical-edit surface is a MAJOR NOGO and leaves the implementer with a broken build. | When adding a parameter to a widely-called function, fresh-grep the count THIS session, list every site, and lean on the whole-tree compile as the safety net. Fix stale comments that assert a now-wrong count. |
| Blocking acquire on the HTTP thread pool | Considered `acquire()` (blocking) so over-cap requests wait for a slot instead of being rejected | cpp-httplib serves requests on a fixed-size thread pool; a blocked thread is one of the threads being protected. Enough blocked waiters deadlock the pool — no thread can ever release. | Use non-blocking `try_acquire()` and reject (503) over-cap; never block on the pool you are protecting. |
| Copying the cap heuristic from a different domain | Picked default `64` via `max_inflight ≈ memory_budget / 1MB`, a heuristic lifted from a Python/Scylla context | Real worst-case residency depends on body buffering + JSON parse expansion (1 MB body → several MB of `nlohmann::json`), so 64 may be optimistic and OOM under load. | The default is UNVALIDATED — load-test it. Making it env-configurable was correct, but call out that the default number itself is a guess until measured. |

## Results & Parameters

| Parameter | Value | Notes |
| --- | --- | --- |
| Mechanism | Per-handler RAII wrapper (`with_resource_cap`) | Decorates each throttled handler; the guard acquires at entry and releases at scope exit (normal/early/throw). The guard is the production mechanism, not test-only. Exempt routes are never wrapped — no exclusion list. |
| Env var | `MAX_INFLIGHT_REQUESTS` | Default `64` (starting heuristic; a 1 MB body can expand to several MB as parsed JSON — load-test the real ceiling). `0` = disabled (cap off, tests/fixtures unaffected). |
| Semaphore type | `std::counting_semaphore<1<<20>` with a `std::mutex`+counter fallback behind the same API | C++20 target ≠ `<semaphore>` guaranteed present — add a build-time compile check and fall back to a mutex+counter if absent. `try_acquire()` is non-blocking by spec. Thread-safety rides on the semaphore's internal atomics (or the mutex fallback); no app-level shared mutable state exposed. |
| Over-cap response | `503 Service Unavailable` + `Retry-After: 1` | Reject, do not block — blocking on the fixed HTTP thread pool would deadlock it. Domain-level translation of the "no slot" primitive at the boundary; explicit + observable, not a silent drop. |
| Handler capture | `[lim, h = std::move(h)]` BY VALUE | cpp-httplib copies handlers into `std::function`; by-ref / `[&]` capture dangles (canonical capture-UB rule). |
| Acquire point | Inside the throttled handler, after auth + rate-limit | Cheap rejections must not consume a slot; exempt routes are unwrapped. |
| Throttling key (inherited) | `req.remote_addr` (existing per-IP RateLimiter) | UNVERIFIED behind Tailscale / proxy / NAT: if traffic is proxied, all clients collapse to one key. Not changed by this plan, but an inherited risk worth a verification note. |

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| ProjectAgamemnon | issue #273 planning (R0) | Original plan-stage only — no code written, built, or run. R0 received a NOGO for the split pre/post-routing lifecycle assumption and the undercounted call-site surface. |
| ProjectAgamemnon | issue #273 re-plan (R1 after R0 NOGO) | Plan-stage only — no code written, built, or run. R1 pivots to the per-handler RAII wrapper (resolving R0's #1 risk) and asserts the call-site count from a fresh grep (9 sites across 8 files). Still unverified against a running binary. |
