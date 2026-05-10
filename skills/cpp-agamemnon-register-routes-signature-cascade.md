---
name: cpp-agamemnon-register-routes-signature-cascade
description: "Use when: (1) Agamemnon C++ PR fails with 'error: no matching function for call to register_routes' in test files, (2) PR fails with undefined references to a new feature class after CMakeLists was updated, (3) clang-tidy fails with misc-use-anonymous-namespace on static functions in src/nats_client.cpp, (4) PR's CMakeLists.txt was updated but test/CMakeLists.txt or agamemnon_lib source list was not. Covers the three recurring error classes when a PR adds a new parameter to register_routes() in routes.hpp and only patches server_main.cpp but leaves test call-sites stale."
category: debugging
date: 2026-05-09
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - cpp
  - agamemnon
  - register_routes
  - cmake
  - test-fixture
  - signature-mismatch
  - undefined-reference
  - clang-tidy
  - anonymous-namespace
  - agamemnon_lib
---

# C++ Agamemnon register_routes Signature Cascade

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-09 |
| **Objective** | Diagnose and fix the three recurring CI error classes when a ProjectAgamemnon PR adds a new parameter to `register_routes()` in `routes.hpp` |
| **Outcome** | Successful — applied to 8 Agamemnon PRs in a single session; all CI build/static-analysis clusters went green and PRs began merging via squash auto-merge |
| **Verification** | verified-ci |

## When to Use

- A ProjectAgamemnon PR fails with `error: no matching function for call to 'register_routes'` in test files (`test/src/test_routes_malformed.cpp`, `test/src/test_routes.cpp`, `test/src/test_nats_client.cpp`, etc.)
- PR fails with `undefined reference to` a new feature class (e.g., `AuthMiddleware`, `RateLimiter`, `MetricsRegistry`, `Orchestrator`) at link time across all test executables
- `clang-tidy` CI job fails with `[misc-use-anonymous-namespace]` on a `static` function in `src/nats_client.cpp`
- PR author updated `include/projectagamemnon/routes.hpp` and `src/server_main.cpp` but did NOT update test fixture call sites or `agamemnon_lib` source list in `CMakeLists.txt`
- CI failure survives a clean rebase onto main — this is a bug in the PR's own diff, not a merge conflict

## Verified Workflow

### Quick Reference

```bash
# Step 1: Get the job ID for the failing build
RUN=$(gh run list --repo HomericIntelligence/ProjectAgamemnon \
  --branch <branch> --workflow "Build and Test" --limit 1 \
  --json databaseId --jq '.[0].databaseId')
JOB=$(gh run view $RUN --repo HomericIntelligence/ProjectAgamemnon \
  --json jobs --jq '.jobs[] | select(.name=="ubuntu-24.04-gcc-debug") | .databaseId')

# Step 2: Extract actual compile/link errors
gh api repos/HomericIntelligence/ProjectAgamemnon/actions/jobs/$JOB/logs 2>&1 \
  | grep -E "error:|undefined reference" | head -10

# Step 3: Find all register_routes call sites
grep -rn "register_routes" src/ test/

# Step 4: Read current signature
cat include/projectagamemnon/routes.hpp | grep -A3 "register_routes"

# Step 5: Check agamemnon_lib source list
grep -n "src/" CMakeLists.txt | head -30
```

### Detailed Steps

#### Class A — `error: no matching function for call to 'register_routes'`

The PR adds a new N-th argument to `register_routes()` in `routes.hpp` and `server_main.cpp`
but test files still call the old (N-1)-argument signature.

1. Run `grep -rn "register_routes" src/ test/` to enumerate every call site.
2. Read `include/projectagamemnon/routes.hpp` to determine the current full signature.
3. For each failing test file, open it and locate the test fixture struct/class.
4. Check whether the fixture already has an instance of the new parameter type (e.g., `auth_`, `metrics_`, `orchestrator_`, `rate_limiter_`).
5. If the instance is missing, instantiate it in the fixture using a minimal/default constructor.
6. Update the `register_routes(...)` call site to pass the new argument.
7. Repeat for every test file reported in the error log.

Example — adding `AuthMiddleware&` as the 4th argument:

```cpp
// Before (stale)
register_routes(app, db_, config_);

// After — fixture already has auth_ member
register_routes(app, db_, config_, auth_);

// After — fixture was missing auth_; add it:
// struct Fixture {
//   ...
//   AuthMiddleware auth_{config_};   // <- add this
// };
register_routes(app, db_, config_, auth_);
```

#### Class B — Undefined references at link time

The PR introduces a new `.cpp` file (e.g., `src/auth.cpp`, `src/rate_limiter.cpp`,
`src/metrics.cpp`, `src/orchestrator.cpp`) but does not add it to the `agamemnon_lib`
STATIC library source list in `CMakeLists.txt`.

1. Run `grep -n "src/" CMakeLists.txt` to see the current `agamemnon_lib` source list.
2. Add the missing `.cpp` file to the `add_library(agamemnon_lib STATIC ...)` block.
3. If the new feature pulls in an external dependency (e.g., libcurl):
   - Add `find_package(CURL REQUIRED)` near the top of `CMakeLists.txt`.
   - Add `target_link_libraries(agamemnon_lib PUBLIC CURL::libcurl)`.
   - Add the dep to `conanfile.py` if Conan manages it.
4. If test executables need to link against the new library, check `test/CMakeLists.txt`
   and add `target_link_libraries(<test_exe> PRIVATE <new_lib>)`.

Example — `src/metrics.cpp` not in build:

```cmake
# Before
add_library(agamemnon_lib STATIC
  src/server.cpp
  src/routes.cpp
  src/nats_client.cpp
)

# After
add_library(agamemnon_lib STATIC
  src/server.cpp
  src/routes.cpp
  src/nats_client.cpp
  src/metrics.cpp     # <- add
)
```

#### Class C — `[misc-use-anonymous-namespace]`

`clang-tidy` flags `static` free functions in `.cpp` files (most commonly
`src/nats_client.cpp`) with `[misc-use-anonymous-namespace]`. Promote them to
error in CI by replacing `static` with an anonymous namespace.

```cpp
// Before
static bool is_infra_error(natsStatus s) { ... }

// After
namespace {
bool is_infra_error(natsStatus s) { ... }
}  // namespace
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Rebase onto main | Rebasing the PR onto latest main to fix "register_routes" errors | Test call-sites are stale in the PR's own diff — clean rebase doesn't fix them | This is a PR-internal bug, not a merge-conflict artifact |
| Only patching routes.hpp | Updating the declaration but not propagating the new arg to test fixtures | Compiler finds the new signature but all test call-sites still call the old arity | Always `grep -rn register_routes src/ test/` after changing the signature |
| Only adding .cpp to CMakeLists.txt root | Adding `src/metrics.cpp` to `CMakeLists.txt` but not to `test/CMakeLists.txt` link lines | Test executables still get undefined-reference errors because they don't link `agamemnon_lib` transitively | Check both `CMakeLists.txt` and `test/CMakeLists.txt` for link-line gaps |

## Results & Parameters

### PR Table (Verified on 8 PRs, 2026-05-09)

| PR | New 4th arg | What was missed | Error class |
|----|-------------|-----------------|-------------|
| #154 (HMAS) | `Orchestrator&` | `server_main.cpp:77` + test fixtures | A |
| #259 (auth) | `AuthMiddleware&` | `server_main.cpp` + test fixtures | A |
| #270 (body cap) | (none — separate issue) | `test/CMakeLists.txt` missing test_routes block | B |
| #292 (metrics) | `MetricsRegistry&` | `server_main.cpp:77` + test fixture missing member | A+B |
| #336 (pagination) | (params with no default) | 25 test call-sites | A |
| #342 (rate-limit) | `RateLimiter&` | `server_main.cpp:97` + test fixtures | A |
| #160 | (multiple) | `agamemnon_lib` missing `.cpp` | B |
| #285 | `static` fn | `src/nats_client.cpp` static fn | C |

### Diagnostic Log Extraction

```bash
# Get compile errors from CI without downloading full log
gh api repos/HomericIntelligence/ProjectAgamemnon/actions/jobs/$JOB/logs 2>&1 \
  | grep -E "error:|undefined reference" | head -10

# Useful patterns to grep for in CI output:
#   "no matching function for call to 'register_routes'"
#   "undefined reference to"
#   "[misc-use-anonymous-namespace]"
```

### Branch Protection Note

`strict_required_status_checks_policy: false` on ProjectAgamemnon — passing checks on
ANY commit SHA in the PR satisfy required checks. After pushing a fix, the auto-merge
fires on the PR's current HEAD without needing to wait for the base to be up-to-date.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/ProjectAgamemnon | 8 PRs fixed in one session (2026-05-09) | PRs #154, #259, #270, #292, #336, #342, #160, #285 — all went green and merged |
