---
name: cpp-httplib-prerouting-audit-event-planning
description: "Use when planning (not yet implementing) a feature that emits an audit/log event to NATS from a cpp-httplib pre-routing handler in a C++ service: (1) injecting a long-lived dependency (rate limiter, publisher) into set_pre_routing_handler, (2) rate-limiting events per client IP, (3) reusing a high-level publish_log/NATS envelope wrapper, (4) adding client IP (remote_addr) to a payload that triggers PII-audit-doc maintenance, (5) deciding test doubles for a fire-and-forget publisher."
category: architecture
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [cpp, cpp-httplib, pre-routing, nats, audit, rate-limiter, pii, planning, lambda-capture, agamemnon]
---

# C++ cpp-httplib Pre-Routing Audit-Event Emission: Planning Skill

## Overview

| Field | Value |
| --- | --- |
| Date | 2026-06-19 |
| Objective | Capture durable, reusable planning lessons for emitting an audit/log event to a NATS subject from a cpp-httplib pre-routing handler, rate-limited per client IP |
| Outcome | Implementation plan produced (planning artifact only — no code written, built, or tested) |
| Verification | unverified |
| Context | ProjectAgamemnon issue #263 — emit auth-failure events to `hi.logs.agamemnon.auth_failure` from the cpp-httplib pre-routing handler, rate-limited per IP |

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

## When to Use

Apply this skill when **planning** (before writing code) a change in a C++ cpp-httplib + NATS service where you must:

- Inject a long-lived dependency (rate limiter, NATS publisher) into a `set_pre_routing_handler` lambda.
- Emit a structured audit/log event from the request hot path on some condition (auth failure, suspicious request).
- Rate-limit those emitted events per client IP ("≤ N events / IP / second").
- Reuse an existing high-level publish wrapper that builds a structured log envelope, rather than the raw NATS publish API.
- Add the client IP (`remote_addr`) to a serialized payload — which changes the PII posture and may falsify an existing security/PII audit doc.
- Choose a test double for a fire-and-forget publisher whose failures are swallowed.

**Key triggers:**

- You are about to plan an edit to a `register_routes(...)`-style registrar that captures dependencies into a handler lambda.
- The handler lambda outlives the function that registers it (httplib copies the lambda).
- A flood of events must be collapsed to a bounded rate per source IP.
- An existing audit/PII doc asserts "no IP addresses are serialized."

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms. The section is titled "Verified Workflow" only because the repository validator (`scripts/validate_plugins.py`) requires that literal heading; the `verification: unverified` frontmatter is authoritative.

### Quick Reference

```cpp
// CORRECT — pointer-capture a long-lived dep (owned by main()) so the
// httplib-copied lambda does not dangle after register_routes returns.
RateLimiter* audit_limiter = &audit_limiter_ref;   // separate instance!
NatsPublisher* pub = &publisher_ref;
server.set_pre_routing_handler(
    [audit_limiter, pub](const httplib::Request& req, httplib::Response& res) {
        if (auth_failed(req) && audit_limiter->allow(req.remote_addr)) {
            pub->publish_log(/*subject*/ "hi.logs.agamemnon.auth_failure",
                             /*level*/ "warn",
                             /*message*/ "auth failure",
                             /*metadata*/ {{"remote_addr", req.remote_addr},
                                           {"path", req.path},
                                           {"method", req.method}});
        }
        return httplib::Server::HandlerResponse::Unhandled;
    });
```

```cpp
// ANTI-PATTERN — reference capture of a stack local: BOTH bugs at once.
{
    RateLimiter audit_limiter(1.0, 1.0);                 // stack local
    server.set_pre_routing_handler([&audit_limiter](...) // [&] dangles
        { ... });
}   // audit_limiter destroyed here; lambda copy still references it -> UB
```

### Step 1 — Lambda capture: pointer-capture long-lived deps, never reference-capture

cpp-httplib **copies** the registered lambda and the copy outlives the registrar's stack frame. A reference capture (`[&x]`) to anything that dies when the registrar returns dangles and is undefined behavior. Always pointer-capture long-lived dependencies (`[xp]` where `Xp* xp = &x`). **Verify the target file's existing convention before planning the edit** — in this codebase `ProjectAgamemnon/src/routes.cpp` (around lines 187-189) documents exactly this rule; match it.

### Step 2 — Reuse a tested token-bucket RateLimiter; construct a SEPARATE instance

For "N events per IP per second," reuse the existing, tested token-bucket `RateLimiter` rather than hand-rolling a per-IP last-seen map. `RateLimiter(1.0, 1.0)` = 1 token/sec, burst 1 = exactly "≤ 1 event / IP / sec." The existing class already maintains a per-IP map + mutex + stale eviction to bound memory.

**CRITICAL:** Do NOT reuse the request-path rate-limiter instance for the audit gate. That conflates concerns and consumes request tokens. Construct a **separate** limiter instance dedicated to the audit gate.

### Step 3 — Ownership/lifetime: pass the new dep by reference through the registrar; audit ALL callers

The handler lambda outlives the registrar, so a stack-local dependency constructed inside the registrar dangles (see Step 1). Therefore:

- Own the new dependency in `main()` (long-lived).
- Pass it **by reference** through the registrar's signature (e.g. `register_routes(..., RateLimiter& audit_limiter)`).
- Pointer-capture it inside the lambda.

A signature change to `register_routes(...)` forces a **fan-out caller audit**. This is a **required planning step, not an afterthought** — a missed caller is a compile break:

```bash
grep -rn "register_routes(" src/ test/
```

Enumerate EVERY call site: production entrypoint (`src/server_main.cpp` here), all unit-test fixtures, and integration tests. Update each.

### Step 4 — Prefer the high-level `publish_log` wrapper over the raw NATS publish API

The existing `publish_log` wrapper already:

- Builds the structured ADR-005 envelope (timestamp / service / level / message / metadata).
- Is fire-and-forget, retries, and DLQs on broker failure so the **request path never blocks or throws**.
- Sidesteps low-level nats.c gotchas (`jsErrCode`, `&jerr`, `jsPubAck_Destroy`).

Map the issue-required fields into `metadata`. Do **NOT** duplicate `timestamp` into metadata — the wrapper already stamps it at the envelope top level.

### Step 5 — Adding client IP changes the PII posture: update the audit doc as a deliverable

Adding `remote_addr` to any serialized payload changes the PII posture. If a security/PII audit doc exists and asserts "no IP addresses are serialized," **updating that doc to record the new IP-bearing subject is a required deliverable of the plan**, not optional. Otherwise the audit silently becomes false. Treat truthful-audit-doc maintenance as an **acceptance criterion**.

### Step 6 — Test-double asymmetry drives the test design

The integration fixture used a real client against a **DOWN** broker. The fire-and-forget publisher swallows failures, so that fixture **cannot** assert the emit happened. Switch the test to the recording fake (`FakeNatsPublisher`), which records publish subjects.

**KNOWN LIMITATION to flag to reviewers:** the fake records only the **subject** string, not the payload/metadata. A subject-count assertion proves (a) the event fired and (b) rate-limiting collapses a flood — but does **NOT** prove the `remote_addr` / `path` / `method` field contents. If field-content verification is required, extend the fake to capture metadata, or use a real NATS subscriber.

### Step 7 — Risks / unverified reliances (carry into implementation)

These assumptions were relied upon during planning but were NOT verified against HEAD — confirm during implementation:

- Exact line numbers in `routes.cpp` / `nats_client.cpp` were read once but not re-verified against HEAD; line drift is possible.
- `src/server_main.cpp` was asserted to be the only non-test `register_routes` caller, but the confirming `grep` was NOT actually run during planning. Unverified — locate during implementation.
- The full set of test/integration callers of `register_routes` was inferred, not exhaustively grepped.
- `FakeNatsPublisher::publish_log` was read and records subject only (true at read time). Substituting the fixture's real `NatsClient` with `FakeNatsPublisher` should be compatible with `Orchestrator`'s constructor (it takes a `NatsPublisher&`), but the substitution was not compiled.
- `validate_plugins.py`'s exact required section names were not known at plan time — run it and adapt the section headings to whatever it enforces.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Reference-capture a dependency into the pre-routing lambda | `server.set_pre_routing_handler([&dep](...){...})` capturing a dep that lives in the registrar's frame | httplib copies the lambda; the copy outlives `register_routes`' stack frame, so the reference dangles (UB) | Pointer-capture long-lived deps (`[depp]`, `Dep* depp = &dep`); own the dep in `main()` and pass it by reference through the registrar |
| Reuse the request-path rate limiter for the audit gate | Call `request_limiter.allow(ip)` to gate audit events | Conflates two concerns and consumes request-path tokens, throttling real requests and corrupting both budgets | Construct a SEPARATE `RateLimiter(1.0, 1.0)` instance dedicated to the audit gate |
| Construct the limiter as a stack local inside the registrar | `RateLimiter audit_limiter(1.0,1.0);` declared inside `register_routes` then captured | The handler lambda outlives the registrar, so the local is destroyed while the lambda copy still references it | Make the dependency long-lived (owned by `main()`), pass by reference through the registrar signature |
| Assert the emit via the down-broker integration fixture | Real `NatsClient` against a DOWN broker, then assert the event was published | The fire-and-forget publisher swallows broker failures, so nothing observable proves the emit | Use the recording `FakeNatsPublisher` (records subjects); flag that it does not capture payload/metadata |
| Add `remote_addr` to the payload without touching the PII audit doc | Serialize client IP into metadata and ship | An existing PII audit doc asserting "no IPs serialized" becomes silently false | Treat updating the PII/security audit doc as a required deliverable and acceptance criterion |

## Results & Parameters

### Planning Checklist (carry into the implementation issue)

- [ ] Confirm the file's existing capture convention (`routes.cpp:~187-189`) and pointer-capture all long-lived deps.
- [ ] Construct a SEPARATE `RateLimiter(1.0, 1.0)` for the audit gate (do not reuse the request limiter).
- [ ] Own the limiter + publisher in `main()`; pass by reference through `register_routes(...)`.
- [ ] Run `grep -rn "register_routes(" src/ test/` and update EVERY caller (prod + unit + integration).
- [ ] Use `publish_log` (ADR-005 envelope); map issue fields into `metadata`; do NOT duplicate `timestamp`.
- [ ] Update the PII/security audit doc to record the new IP-bearing subject.
- [ ] Switch the emit test to `FakeNatsPublisher`; assert subject count (fired + flood collapsed).
- [ ] Flag the field-content gap; extend the fake or use a real subscriber if content checks are required.
- [ ] Re-verify all line numbers and the `server_main.cpp` sole-caller claim against HEAD.

### Key Parameters

| Parameter | Value | Rationale |
| --- | --- | --- |
| `RateLimiter(tokens_per_sec, burst)` | `(1.0, 1.0)` | 1 token/sec, burst 1 = exactly "≤ 1 event / IP / sec" |
| Capture style | pointer (`[xp]`) | httplib copies the lambda; reference capture of a non-lived dep dangles |
| Audit limiter instance | separate from request limiter | Avoid consuming request tokens / conflating concerns |
| Publish API | `publish_log` wrapper | Builds ADR-005 envelope; fire-and-forget; retries + DLQ; never blocks request path |
| `timestamp` in metadata | omit | Wrapper stamps it at envelope top level |
| Test double | `FakeNatsPublisher` | Records subjects; down-broker real fixture can't observe a swallowed failure |

### Example Subject / Envelope Mapping

```
subject : hi.logs.agamemnon.auth_failure
level   : warn
message : "auth failure"
metadata: { remote_addr, path, method }   # timestamp stamped by wrapper, NOT here
```

## Related Skills

- `cpp-rate-limiter-test-fixture-burst-capacity-trap` — token-bucket `RateLimiter` constructor is `(tokens_per_sec, burst_capacity)`, not `(max_requests, window)`; relevant when testing the audit gate.
- `architecture-pre-discovery-worker-guard-pattern` — general pattern for resolving long-lived state before entering a hot path.

## Tags

`#cpp` `#cpp-httplib` `#pre-routing` `#nats` `#audit` `#rate-limiter` `#pii` `#planning` `#lambda-capture` `#agamemnon`
