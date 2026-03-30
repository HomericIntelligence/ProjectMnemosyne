---
name: cpp-httplib-lambda-capture-ub
description: "Fix dangling reference UB in cpp-httplib route handler lambdas. Use when: (1) registering cpp-httplib routes that capture shared state by reference, (2) debugging crashes in HTTP handlers after register_routes() returns, (3) reviewing cpp-httplib lambda captures."
category: debugging
date: 2026-03-30
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - cpp-httplib
  - lambda
  - undefined-behavior
  - dangling-reference
  - cpp20
---

# cpp-httplib Lambda Capture Dangling Reference UB

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-30 |
| **Objective** | Fix undefined behavior in cpp-httplib route handlers that capture shared state |
| **Outcome** | Successful — root cause identified and fixed across 20+ route handlers |
| **Verification** | verified-local |

## When to Use

- Registering cpp-httplib route handlers via a `register_routes(server, store, nats)` helper function
- Route handlers that capture shared state (Store, NatsClient, etc.)
- Debugging HTTP handlers that work in simple tests but crash/corrupt under load
- Code review of any cpp-httplib route registration

## Verified Workflow

### Quick Reference

```cpp
// WRONG — dangling reference after register_routes() returns:
void register_routes(httplib::Server& server, Store& store) {
  server.Get("/v1/agents", [&store](auto& req, auto& res) {
    // store reference dangles if register_routes stack frame is gone
    // cpp-httplib copies the lambda by value into internal storage
  });
}

// CORRECT — capture pointer by value:
void register_routes(httplib::Server& server, Store& store) {
  Store* sp = &store;  // pointer lives in lambda's capture, not stack
  server.Get("/v1/agents", [sp](auto& req, auto& res) {
    // sp is a copy of the pointer — safe after register_routes returns
    res.set_content(sp->list_agents().dump(), "application/json");
  });
}
```

### Detailed Steps

1. In `register_routes()`, extract raw pointers from references at the top:
   ```cpp
   Store* sp = &store;
   NatsClient* np = &nats;
   ```
2. Capture `sp` and `np` by value in all lambdas: `[sp, np](...)`
3. Never capture `&store` or `&nats` — they're function parameters on the stack
4. This is safe because Store and NatsClient outlive the server (created in main())

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `[&store]` capture | Reference capture of function parameter | cpp-httplib stores handlers in `std::function` by value — the lambda outlives the `register_routes` stack frame, leaving a dangling reference | cpp-httplib copies lambdas into internal handler storage; any by-ref capture of a local/parameter is UB |
| `[&]` default capture | Capture everything by reference | Same problem — all references dangle after function returns | Never use `[&]` in cpp-httplib route handlers |

## Results & Parameters

```cpp
// Pattern used across all 20+ route handlers in ProjectAgamemnon:
void register_routes(httplib::Server& server, Store& store, NatsClient& nats) {
  Store* sp = &store;
  NatsClient* np = &nats;

  server.Get("/v1/health", [](auto&, auto& res) { /* no captures needed */ });
  server.Get("/v1/agents", [sp](auto&, auto& res) { /* uses sp-> */ });
  server.Post("/v1/agents", [sp, np](auto& req, auto& res) { /* uses both */ });
  // ... all handlers follow same pattern
}
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectAgamemnon | E2E pipeline implementation | 20+ route handlers fixed from [&store] to [sp] capture pattern |
