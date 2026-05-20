---
name: cpp-build-and-runtime-bug-patterns
description: "Use when: (1) a C++ PR fails with 'no matching function for call to register_routes' or undefined references after a signature change, (2) std::atomic members cause POSIX socket calls to resolve as std::bind via ADL, (3) a [[deprecated]] struct field causes the struct's own .cpp to fail under -Werror, (4) cpp-httplib route handler lambdas crash due to dangling reference UB after register_routes returns, (5) nlohmann/json .value(key, nullptr).is_null() fails to compile with nullptr_t type error, (6) cmake configure succeeds but ctest reports No tests were found in a scaffold repo."
category: debugging
date: 2026-05-19
version: "1.0.0"
user-invocable: false
history: cpp-build-and-runtime-bug-patterns.history
tags:
  - cpp
  - cpp20
  - agamemnon
  - cmake
  - register_routes
  - signature-mismatch
  - undefined-reference
  - clang-tidy
  - atomic
  - posix
  - adl
  - socket
  - deprecated
  - pragma
  - werror
  - cpp-httplib
  - lambda
  - undefined-behavior
  - dangling-reference
  - nlohmann-json
  - nullptr
  - ctest
  - scaffold
---

# C++ Build and Runtime Bug Patterns

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-19 |
| **Objective** | Diagnose and fix six recurring C++ build and runtime defect classes in HomericIntelligence scaffold repos (Agamemnon/Nestor/Charybdis/Keystone) |
| **Outcome** | All patterns verified across CI and local builds; applied to 10+ PRs across ProjectAgamemnon and ProjectKeystone |
| **Verification** | verified-ci (patterns A/B/C/D/F); verified-local (pattern E) |

## When to Use

- A ProjectAgamemnon PR fails with `error: no matching function for call to 'register_routes'` in test files or at link time with undefined references (Pattern A/B)
- `clang-tidy` fails with `[misc-use-anonymous-namespace]` on static functions in `src/nats_client.cpp` (Pattern C)
- A class with `std::atomic<int>` members suddenly fails to compile because `bind()` resolves as `std::bind` instead of POSIX `bind()` (Pattern D)
- Adding `[[deprecated("...")]]` to a struct field causes the struct's own `.cpp` to fail under `-Werror,-Wdeprecated-declarations` (Pattern E)
- cpp-httplib route handlers crash or corrupt data under load — lambdas capture function parameters by reference (Pattern F)
- `json.value("key", nullptr).is_null()` causes a compile error about `nullptr_t` not having members (Pattern G)
- `ctest` reports "No tests were found!!!" even though the test binary was compiled in a scaffold repo (Pattern H)

## Verified Workflow

### Quick Reference

```bash
# Pattern A — find all register_routes call sites after signature change
grep -rn "register_routes" src/ test/
cat include/projectagamemnon/routes.hpp | grep -A3 "register_routes"

# Pattern B — find missing sources in agamemnon_lib
grep -n "src/" CMakeLists.txt | head -30

# Pattern C — clang-tidy anonymous namespace
# Replace: static bool is_infra_error(...) { ... }
# With:    namespace { bool is_infra_error(...) { ... } }  // namespace

# Pattern D — ADL fix: add :: prefix + .load() to all POSIX socket calls
grep -n "bind\|listen\|accept\|setsockopt\|getsockname\|close\|pfd\.fd" src/file.cpp

# Pattern E — pragma suppression for [[deprecated]] internal use
# Wrap internal assignments with:
#   #pragma GCC diagnostic push
#   #pragma GCC diagnostic ignored "-Wdeprecated-declarations"
#   ... assignment ...
#   #pragma GCC diagnostic pop

# Pattern G — nlohmann/json nullptr fix
# Wrong:   obj.value("field", nullptr).is_null()
# Correct: obj.value("field", json(nullptr)).is_null()

# Pattern H — cmake scaffold test path fix
grep "add_executable" test/CMakeLists.txt
# Bad:  add_executable(${PROJECT_NAME}_tests test/src/test_main.cpp)
# Good: add_executable(${PROJECT_NAME}_tests src/test_main.cpp)
```

### Pattern A — `register_routes()` Signature Cascade

A PR adds a new argument to `register_routes()` in `routes.hpp` and `server_main.cpp` but leaves test call-sites stale.

1. Run `grep -rn "register_routes" src/ test/` to enumerate every call site.
2. Read `include/projectagamemnon/routes.hpp` for the full current signature.
3. For each failing test file, check whether the fixture already has an instance of the new parameter type.
4. If missing, instantiate it in the fixture using a minimal/default constructor.
5. Update each `register_routes(...)` call to pass the new argument.

```cpp
// Before (stale fixture)
register_routes(app, db_, config_);

// After — add new member and update call
// struct Fixture { ... AuthMiddleware auth_{config_}; };
register_routes(app, db_, config_, auth_);
```

### Pattern B — Undefined References at Link Time

A new `.cpp` file is added but not included in the `agamemnon_lib` STATIC source list.

1. Check `grep -n "src/" CMakeLists.txt` to see the current `agamemnon_lib` source list.
2. Add the missing `.cpp` to the `add_library(agamemnon_lib STATIC ...)` block.
3. If the new feature pulls in an external dependency (e.g., libcurl), add `find_package` and `target_link_libraries` entries.
4. Also check `test/CMakeLists.txt` for test executables that may need their own link-line updates.

```cmake
# After — add missing source
add_library(agamemnon_lib STATIC
  src/server.cpp
  src/routes.cpp
  src/nats_client.cpp
  src/metrics.cpp     # <- add missing file
)
```

### Pattern C — `[misc-use-anonymous-namespace]`

`clang-tidy` flags `static` free functions in `.cpp` files. Replace with an anonymous namespace.

```cpp
// Before
static bool is_infra_error(natsStatus s) { ... }

// After
namespace {
bool is_infra_error(natsStatus s) { ... }
}  // namespace
```

### Pattern D — std::atomic ADL Collision with POSIX `bind()`

When `<atomic>` is included (directly or transitively), `std::bind` enters scope. Unqualified `bind(fd, ...)` triggers ADL and finds `std::bind`, which cannot copy-construct `std::atomic<int>`.

**Two fixes required at every call site:**
- Add `::` prefix to resolve to global-namespace POSIX function.
- Add `.load()` to extract the `int` value from the atomic member.

```cpp
// Before (broken)
bind(server_fd_, (struct sockaddr*)&address, sizeof(address));
htons(port_);
pfd.fd = server_fd_;

// After (correct)
::bind(server_fd_.load(), (struct sockaddr*)&address, sizeof(address));
htons(port_.load());          // htons: no :: needed, but .load() required
pfd.fd = server_fd_.load();  // struct field: no :: but .load() required
::setsockopt(server_fd_.load(), SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
::listen(server_fd_.load(), BACKLOG);
int client_fd = ::accept(server_fd_.load(), (struct sockaddr*)&addr, &len);
close(server_fd_.load());     // close: no ADL collision but needs .load()
```

### Pattern E — `[[deprecated]]` Field Causes Own .cpp to Fail

Adding `[[deprecated("...")]]` to a struct member forces the struct's own implementation file to suppress the warning for internal legacy assignments.

```cpp
// Header — add deprecation marker
struct KeystoneMessage {
  [[deprecated("Use 'action' field instead; 'command' will be removed in v3.0")]]
  std::string command;
};
```

```cpp
// .cpp — wrap internal assignments with diagnostic suppression
// Single assignment:
_Pragma("GCC diagnostic push")
_Pragma("GCC diagnostic ignored \"-Wdeprecated-declarations\"")
msg.command = cmd;
_Pragma("GCC diagnostic pop")

// Block of assignments:
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdeprecated-declarations"
msg.command = actionTypeToString(action);
msg.command = "CANCEL_TASK";
#pragma GCC diagnostic pop
```

Both `#pragma GCC diagnostic` and `_Pragma("GCC diagnostic ...")` work in GCC and Clang. No separate `#pragma clang diagnostic` is needed.

### Pattern F — cpp-httplib Lambda Capture Dangling Reference UB

cpp-httplib stores route handlers in `std::function` by value. Any by-reference capture of a `register_routes()` parameter dangling after the function returns.

```cpp
// Wrong — &store dangles after register_routes() returns:
server.Get("/v1/agents", [&store](auto& req, auto& res) { ... });

// Correct — capture raw pointer by value:
void register_routes(httplib::Server& server, Store& store, NatsClient& nats) {
  Store* sp = &store;
  NatsClient* np = &nats;

  server.Get("/v1/agents", [sp](auto&, auto& res) { ... });
  server.Post("/v1/agents", [sp, np](auto& req, auto& res) { ... });
}
```

Never use `[&]` or `[&store]` in cpp-httplib route handlers. Store and NatsClient are safe to hold as pointers because they outlive the server (created in `main()`).

### Pattern G — nlohmann/json `value()` Returns `nullptr_t`

`json::value<T>(key, default)` deduces `T` from the type of `default`. Passing bare `nullptr` deduces `T = std::nullptr_t`, which has no `.is_null()` member.

```cpp
// Wrong
if (obj.value("completedAt", nullptr).is_null()) { ... }

// Correct — force return type to json:
if (obj.value("completedAt", json(nullptr)).is_null()) { ... }

// Alternative — explicit containment check:
if (!obj.contains("completedAt") || obj["completedAt"].is_null()) { ... }
```

### Pattern H — CMake Scaffold Double-Prefix Test Path

The SGSG scaffold template generates `test/CMakeLists.txt` included via `add_subdirectory(test)`. When CMake processes that file, `CMAKE_CURRENT_SOURCE_DIR` is already `<project>/test/`. Using `test/src/test_main.cpp` as the path creates a double prefix: `<project>/test/test/src/test_main.cpp`.

```cmake
# Before (wrong — double test/ prefix)
add_executable(${PROJECT_NAME}_tests test/src/test_main.cpp)

# After (correct — relative to test/ directory)
add_executable(${PROJECT_NAME}_tests src/test_main.cpp)
```

After applying the path fix, ctest may still report "No tests were found!!!" if `int main()` from `src/main.cpp` is compiled into the static library and wins over gtest's `main()` at link time. This is a separate scaffold bug — remove `int main()` from `src/main.cpp` or add a proper `main()` that calls `RUN_ALL_TESTS()` to the test file.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Rebase onto main to fix register_routes errors | Rebased PR onto latest main | Test call-sites are stale in the PR's own diff — clean rebase does not fix them | This is a PR-internal bug, not a merge-conflict artifact; always grep call-sites after signature changes |
| Only patching routes.hpp declaration | Updated declaration but did not propagate new arg to test fixtures | Compiler finds the new signature but all test call-sites call the old arity | Always run `grep -rn register_routes src/ test/` after any signature change |
| Only adding .cpp to root CMakeLists.txt | Added `src/metrics.cpp` to root CMakeLists but not `test/CMakeLists.txt` link lines | Test executables still get undefined-reference errors | Check both `CMakeLists.txt` and `test/CMakeLists.txt` for link-line gaps |
| Just adding `.load()` without `::` on `bind()` | `bind(server_fd_.load(), ...)` | ADL still resolves `bind` as `std::bind` even with plain `int` argument | Both fixes required together: `::` prefix AND `.load()` |
| Only fixing `bind()` socket call | Fixed bind, left setsockopt/getsockname/listen with atomic members | Other call sites still pass `std::atomic<int>` directly to POSIX APIs | Audit ALL socket call sites with grep after atomic member changes |
| Treating atomic-bind as a simple type error | Thought it was about int vs. atomic conversion | The real issue is ADL + name lookup, not just type conversion | `std::bind` in scope from `<functional>` (via `<atomic>`) hijacks unqualified `bind()` |
| Removing `[[deprecated]]` to silence CI | Removed deprecation annotation | Defeats the purpose of the PR; external callers lose the migration warning | Keep the deprecation; use pragma suppression for internal legacy sites only |
| Refactoring internals in same deprecation PR | Migrated all internal uses of deprecated field in same PR | Out of scope; increases blast radius, conflates concerns, reduces reviewability | Do pragma suppression now; schedule internal migration as follow-up issue |
| `[&store]` capture in cpp-httplib route handler | Captured Store reference in lambda | cpp-httplib copies lambdas into `std::function` storage; stack frame is gone by first request | Never use `[&]` or `[&param]` in cpp-httplib handlers; always capture raw pointer by value |
| `[&]` default capture in cpp-httplib handler | Captured everything by reference | Same dangling-reference UB — all references dangle after `register_routes()` returns | Capture only raw pointers by value in all cpp-httplib route handlers |
| Bare `nullptr` as json::value default | `obj.value("completedAt", nullptr).is_null()` | `json::value<T>` deduces `T = std::nullptr_t` from the default; `nullptr_t` has no `.is_null()` | Pass `json(nullptr)` to force `T = json`; or use `contains()` + `is_null()` check |
| Absolute path in test/CMakeLists.txt | Used `${CMAKE_SOURCE_DIR}/test/src/test_main.cpp` | Works from repo root but breaks when `-S` points elsewhere (Odysseus meta-repo case) | Always use paths relative to `CMAKE_CURRENT_SOURCE_DIR` inside subdirectories |
| Fix only for preset build | Tested with `cmake --preset debug` only | Meta-repo uses `cmake -S <submodule> -B <BUILD_ROOT>/<Name>` which bypasses presets | Verify both build contexts: preset (per-repo) and `-S/-B` (meta-repo) |

## Results & Parameters

### Pattern A PR Table (Verified on 8 Agamemnon PRs, 2026-05-09)

| PR | New Argument | What Was Missed | Error Class |
|----|--------------|-----------------|-------------|
| #154 | `Orchestrator&` | `server_main.cpp:77` + test fixtures | A |
| #259 | `AuthMiddleware&` | `server_main.cpp` + test fixtures | A |
| #270 | (none) | `test/CMakeLists.txt` missing test_routes block | B |
| #292 | `MetricsRegistry&` | `server_main.cpp:77` + test fixture missing member | A+B |
| #336 | params with no default | 25 test call-sites | A |
| #342 | `RateLimiter&` | `server_main.cpp:97` + test fixtures | A |
| #160 | (multiple) | `agamemnon_lib` missing `.cpp` | B |
| #285 | `static` fn | `src/nats_client.cpp` static fn | C |

### Pattern D — POSIX Calls Requiring `::` and `.load()`

| Call | Needs `::` | Needs `.load()` | Notes |
|------|-----------|-----------------|-------|
| `bind()` | Yes | Yes | Primary ADL collision site |
| `setsockopt()` | Yes | Yes | |
| `getsockname()` | Yes | Yes | |
| `listen()` | Yes | Yes | |
| `accept()` | Yes | Yes | |
| `close()` | No | Yes | No ADL collision; still needs value |
| `htons()` | No | Yes | In `<netinet/in.h>`; no collision |
| `pfd.fd =` | No | Yes | Assignment to plain `int` field |

### Pattern E — Pragma Form Selection

| Scenario | Pragma Form | When to Use |
|----------|-------------|-------------|
| Single assignment | `_Pragma("GCC diagnostic push/ignored/pop")` | Inside macros, template bodies, or single-line contexts |
| Block of assignments | `#pragma GCC diagnostic push/ignored/pop` | Cleaner for 2+ consecutive uses in a plain `.cpp` block |

### Scaffold Repos Affected by Pattern H

| Repo | Fix Commit | Date |
|------|-----------|------|
| control/ProjectAgamemnon | 3362f25 | 2026-03-29 |
| control/ProjectNestor | c060492 | 2026-03-29 |
| testing/ProjectCharybdis | a26835e | 2026-03-29 |

### Diagnostic Log Extraction (Patterns A/B/C)

```bash
# Get compile errors from CI without downloading full log
RUN=$(gh run list --repo HomericIntelligence/ProjectAgamemnon \
  --branch <branch> --workflow "Build and Test" --limit 1 \
  --json databaseId --jq '.[0].databaseId')
JOB=$(gh run view $RUN --repo HomericIntelligence/ProjectAgamemnon \
  --json jobs --jq '.jobs[] | select(.name=="ubuntu-24.04-gcc-debug") | .databaseId')
gh api repos/HomericIntelligence/ProjectAgamemnon/actions/jobs/$JOB/logs 2>&1 \
  | grep -E "error:|undefined reference" | head -10

# Key patterns to grep in CI output:
#   "no matching function for call to 'register_routes'"
#   "undefined reference to"
#   "[misc-use-anonymous-namespace]"
#   "call to deleted constructor of 'std::atomic<int>'"
#   "member reference base type 'std::nullptr_t'"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/ProjectAgamemnon | 8 PRs fixed (2026-05-09) — register_routes cascade | PRs #154, #259, #270, #292, #336, #342, #160, #285 — all CI green |
| HomericIntelligence/ProjectAgamemnon | E2E pipeline (2026-03-30) — cpp-httplib lambda UB | 20+ route handlers fixed from `[&store]` to `[sp]` capture pattern |
| HomericIntelligence/ProjectAgamemnon | store.cpp (2026-04-07) — nlohmann nullptr | CI passes after changing `nullptr` to `json(nullptr)` in `update_task()` |
| ProjectKeystone | PR #146 (2026-03-31) — health_check_server.cpp atomics | All sanitizer builds pass: asan/lsan/ubsan/tsan/msan |
| ProjectKeystone | PR #545 (2026-05-09) — deprecated KeystoneMessage::command field | `src/core/message.cpp`, 3 internal assignments wrapped, CI green |
| ProjectAgamemnon, ProjectNestor, ProjectCharybdis | PR #68 (2026-03-29) — CMake scaffold test path | Both per-repo preset and meta-repo `-S/-B` contexts verified |
