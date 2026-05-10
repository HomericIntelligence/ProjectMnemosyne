---
name: cpp-http-client-wrapper-lifetime-equals-object-not-per-call
description: "Keep connection/handle members in wrapper classes — never construct heavy resources per call. Use when: (1) reviewing a PR that rewrites a Client/Connection wrapper from member-owned to per-call construction, (2) the rewrite is justified by 'make methods const' or 'satisfy clang-tidy on mutable members', (3) designing a new wrapper around any connection-holding handle (httplib::Client, TCP socket, DB connection, file handle)."
category: architecture
date: 2026-05-10
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - cpp
  - httplib
  - wrapper-class
  - resource-lifetime
  - clang-tidy
  - mutable
  - design-pattern
---

# C++ HTTP Client Wrapper: Lifetime Equals Object, Not Per-Call

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-10 |
| **Objective** | Preserve member-owned connection design in HTTP/connection wrapper classes under clang-tidy pressure |
| **Outcome** | Successful — main's member-owned `httplib::Client client_` retained; per-call rewrite rejected in PR #83 |
| **Verification** | verified-ci (PR #83 merged after reverting the per-call rewrite) |

## When to Use

- Reviewing a PR that rewrites a Client/Connection wrapper from member-owned to per-call construction
- The rewrite is justified by "make methods const" or "satisfy clang-tidy on mutable members"
- Test suite runtime regressed after a "static analysis cleanup" PR
- Designing a new wrapper around any connection-holding handle (httplib::Client, TCP socket, DB connection, file handle, regex match cache)
- A code review where someone proposes constructing a heavy resource per-call rather than per-object
- clang-tidy complains about a mutable member being mutated by `const` methods

## Verified Workflow

### Quick Reference

```cpp
// PATTERN (preferred): wrapper holds the handle, methods reuse it
class HttpClient {
  mutable httplib::Client client_;  // mutable if methods are const
  std::string base_url_;
public:
  HttpClient(std::string host, int port)
    : client_(host, port), base_url_("http://" + host + ":" + std::to_string(port)) {}

  Response get(const std::string& path) const { return client_.Get(path.c_str()); }
  Response post(const std::string& path, const std::string& body) const {
    return client_.Post(path.c_str(), body, "application/json");
  }
};

// ANTI-PATTERN (reject): construct heavy resource per call
class HttpClient {
  std::string host_;
  int port_;
public:
  Response get(const std::string& path) const {
    httplib::Client c(host_, port_);  // <-- new TCP setup per call
    return c.Get(path.c_str());
  }
};
```

### Detailed Steps

1. **Identify the resource being wrapped.** If the constructor of that resource establishes a connection (TCP handshake, file open, DB auth), it is "heavy" — never construct per-call.

2. **Hold the resource as a member.** The resource's lifetime must equal the wrapper object's lifetime:
   ```cpp
   class HttpTestClient {
     httplib::Client client_;  // member, not local variable
   public:
     explicit HttpTestClient(const std::string& host, int port)
       : client_(host, port) {}
   };
   ```

3. **If clang-tidy complains that const methods mutate the member**, add `mutable`:
   ```cpp
   mutable httplib::Client client_;
   ```
   This is the correct language-level answer. Do NOT remove the member to satisfy the linter.

4. **If you still need targeted suppression**, add `// NOLINT(<rule>)` at the declaration site:
   ```cpp
   mutable httplib::Client client_;  // NOLINT(cppcoreguidelines-avoid-non-const-member-variables)
   ```

5. **Take only the static-analysis hardening from a PR that rewrites the design** (e.g., `WarningsAsErrors: '*'`, suppressor lists, anchored `HeaderFilterRegex` in `.clang-tidy`) — reject the structural rewrite.

6. **Verify test suite runtime** did not regress. Per-call construction multiplies TCP setup cost across every test invocation.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Rewrite `HttpTestClient` to construct `httplib::Client` per call to make methods `const`-qualified | Test suite runtime regression. The wrapping became pointless — the class held nothing. clang-tidy was satisfied at the cost of design coherence. | "Make methods const" is the wrong reason to remove a connection member. The right fix is the `mutable` keyword on the member. |
| 2 | Store `host_` + `port_` as members, construct client locally in each method | Same as Attempt 1 — the data members are meaningless tokens; what matters is the connection, and the connection is now per-call. | If your data members are just constructor arguments echoed back, you don't have a wrapper — you have a pointless indirection. |
| 3 | Make every method static and pass host/port as args | Eliminates the class entirely, breaking every caller; defeats encapsulation. | If you're going to remove the wrapper, REMOVE it — don't reduce it to a stateless namespace. |
| 4 (correct) | Keep member-owned `httplib::Client client_`; add `mutable` if const methods need to mutate it; suppress overly-strict clang-tidy with targeted `// NOLINT` if needed | clang-tidy passes via NOLINT or `mutable`; runtime stays fast; design intent preserved | When clang-tidy complains about a wrapper holding a connection, the language already has the answer: `mutable`. Use it. |

## Results & Parameters

**Design rule:** The lifetime of any wrapped resource is the lifetime of the wrapping object. Never construct heavy resources per method call.

Applies to (not exhaustive):

| Resource Type | Examples |
|--------------|---------|
| HTTP clients | `httplib::Client`, `libcurl` handle, `cpr::Session` |
| TCP/UDP sockets | Raw `int fd`, Boost.Asio `tcp::socket` |
| DB connections | `libpq PGconn*`, `sqlite3*`, `libmysqlclient MYSQL*` |
| File handles | `std::fstream`, POSIX `int fd` |
| Synchronization | `std::mutex`, `std::shared_mutex` (never per-call) |
| Thread pools | `BS::thread_pool`, `std::execution` pools |
| gRPC | `grpc::Channel`, gRPC stubs |
| Message brokers | Redis `redisContext*`, NATS `natsConnection*` |
| Regex caches | `std::regex` (expensive to compile) |

**If clang-tidy complains about the member:**

| clang-tidy Rule | Correct Fix |
|----------------|------------|
| `cppcoreguidelines-avoid-non-const-global-variables` | Not applicable to members (this rule is for globals) |
| Mutable-member rules / const-method violations | Add `mutable` keyword to the member declaration |
| `cppcoreguidelines-avoid-magic-numbers` | Use `constexpr` for port/timeout values |
| `bugprone-easily-swappable-parameters` | Introduce a struct or named types |

The correct trade-off: prefer one targeted `// NOLINT` per occurrence over rearchitecting the class to eliminate the member.

**Verified case — ProjectCharybdis PR #83:**

```
Before (main, CORRECT):     httplib::Client client_;     // member, TCP once at construction
After PR rewrite (REJECTED): httplib::Client(host, port)  // per-call in every method
Resolution:                  Reverted to member; took .clang-tidy hardening only
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectCharybdis | PR #83 fix(static-analysis): promote clang-tidy diagnostics to hard errors | Per-call rewrite of `HttpTestClient` rejected; `mutable httplib::Client client_` pattern retained |
