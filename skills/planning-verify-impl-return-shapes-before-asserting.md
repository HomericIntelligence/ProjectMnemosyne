---
name: planning-verify-impl-return-shapes-before-asserting
description: "When planning route/API tests or API changes from a follow-up issue, the issue body's claimed file paths, handler line numbers, and response shapes are NOT authoritative — read the actual source (store + route) per handler before asserting. Route handlers wrap store return values inconsistently, so a plan that assumes a uniform `{\"agent\": ...}` wrapper produces tests that fail to compile or assert. Use when: (1) planning HTTP route/handler tests from a follow-up or refinement issue, (2) the issue cites a specific test file path or handler line numbers, (3) tests assert on JSON response body shape, (4) you are about to rely on a client-library method overload (e.g. httplib Patch) or framework auto-registration (gtest_discover_tests) without building."
category: documentation
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - verify-before-asserting
  - return-shape
  - route-tests
  - api-tests
  - issue-premise
  - follow-up-issue
  - cpp
  - cpp-httplib
  - gtest
  - source-of-truth
---

# Planning Route/API Tests: Verify Implementation Return-Shapes Before Asserting

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Produce a correct plan for adding route-handler tests from a follow-up issue, without writing assertions against response shapes / file paths / client overloads that the issue claimed but the source does not match |
| **Outcome** | Plan produced for ProjectAgamemnon issue #316; NOT executed — store/route return shapes were read from source, but no `cmake`/`ctest` build was run, the `httplib::Client::Patch` 3-arg overload and gtest auto-registration were assumed, and the new-case count was internally inconsistent |
| **Verification** | unverified |

A follow-up / refinement issue typically asserts current code structure: "the test file is
`test/test_routes.cpp`", "the handler returns `{agent: ...}`", "PATCH uses the 3-arg client
overload." Those are CLAIMS, not a spec. For route/API tests the highest-risk claim is the
**response shape**: route handlers wrap store return values inconsistently, so a plan that
assumes one uniform wrapper will produce tests that fail to compile or assert. Read the
actual `store` AND `routes` source for each handler before writing any assertion.

## When to Use

- Planning HTTP route/handler tests (or an API change) from a follow-up, refinement, or audit issue
- The issue cites a specific test file path or handler line numbers
- Your tests assert on the JSON response body shape (`body["agent"]`, `body["status"]`, …)
- The handlers under test go through a store layer that the route layer may or may not re-wrap
- You are about to rely on a client-library method overload (e.g. `httplib::Client::Patch(path, body, type)`) by analogy to another method
- You are assuming a framework auto-registers new cases (`gtest_discover_tests`) without a build
- You are stating a count of "N new test cases" without recounting the actual `TEST_F` blocks

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

(Verification is `unverified` — the plan below was never built or run. This section is a
**Proposed Workflow**, not a confirmed one.)

### Quick Reference

```bash
# STEP 1 — confirm the test file EXISTS before asserting its contents/line numbers.
#          The issue said test/test_routes.cpp; the real path differed.
ls test/test_routes.cpp 2>/dev/null || echo "MISSING — glob for the real path"
# → not at that path; Glob found test/src/test_routes.cpp instead.
#   (find . -name test_routes.cpp  /  glob '**/test_routes.cpp')

# STEP 2 — read the STORE return statement for each handler (the source of the shape).
grep -nE "start_agent|stop_agent|get_agent_by_name|update_agent|create_agent" src/store.cpp

# STEP 3 — read the ROUTE handler to see whether it re-wraps the store value.
grep -nE "start_agent|stop_agent|get_agent_by_name|update_agent|/v1/agents" src/routes.cpp
# → wrappers are NON-UNIFORM (see table below). Do NOT assume {"agent": ...} everywhere.

# STEP 4 — confirm any client-library overload you rely on against the VENDORED header.
grep -nE "Result Patch\(" <vendored>/httplib.h    # don't infer Patch from Put usage

# STEP 5 — count the actual TEST_F blocks; don't trust the prose count in the plan.
grep -cE "^TEST_F" test/src/test_routes.cpp
```

**Core rule (file path):** the issue's cited file path is a hypothesis. `ls`/Glob the path
and confirm the file exists before asserting its contents or line numbers.

**Core rule (return shape):** for each handler, read BOTH `store.cpp` (what the store
returns) and `routes.cpp` (whether the route re-wraps it). The wrapper is per-handler, not
global.

**Core rule (unverified reliances):** any client-library overload, framework
auto-registration, or "no build needed" claim that was not built is a reviewer checkpoint,
not a fact. Mark the plan `unverified` and point the reviewer at each one.

### Verified return-shape table (ProjectAgamemnon, read from `src/store.cpp` + `src/routes.cpp`)

| Handler | Store returns | Route replies with | Test must assert | Wrong assumption |
|---------|---------------|--------------------|------------------|------------------|
| `start_agent` (POST /start) | `{"status":"online","id":id}` | that body directly | `body["status"]=="online"`, `body["id"]` | `body["agent"]…` (no wrapper) |
| `stop_agent` (POST /stop) | `{"status":"offline","id":id}` | that body directly | `body["status"]=="offline"`, `body["id"]` | `body["agent"]…` (no wrapper) |
| `get_agent_by_name` | the BARE agent | `{"agent": agent}` | `body["agent"]…` | asserting the bare agent at top level |
| `update_agent` (PATCH) | the BARE agent | `{"agent": result}` | `body["agent"]…` | asserting the bare agent at top level |
| `POST /v1/agents/docker` | — | 201 `{"id","agent"}` (same as POST /v1/agents) | status 201, `body["id"]`, `body["agent"]` | a different docker-specific shape |
| `create_agent` | sets initial `status:"offline"` | — | a start test must call /start first to see `"online"` | assuming a freshly-created agent is `"online"` |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust the issue-body test file path | Planned to edit `test/test_routes.cpp` as the issue named | The real path was `test/src/test_routes.cpp` (found via Glob); the issue's path did not exist | Always `ls`/Glob and confirm the file exists before asserting its contents or line numbers — the issue path is a hypothesis |
| Assume a uniform route response wrapper | Planned assertions as `body["agent"][...]` for every handler | `start_agent`/`stop_agent` reply with the bare `{"status","id"}` body (no `agent` wrapper); only `get_agent_by_name`/`update_agent` wrap as `{"agent": …}` | Read `store.cpp` AND `routes.cpp` for each handler; the wrapper is per-handler, not global |
| Assume a created agent is "online" | A start test that asserted `"online"` without first calling /start | `create_agent` sets initial `status` to `"offline"`; `"online"` only appears after a successful /start | Drive the precondition explicitly (call /start) before asserting the post-state |
| Rely on `Patch` 3-arg overload by analogy to `Put` | Planned `client.Patch(path, body, content_type)` inferred from `Put(path, body, content_type)` at test_routes.cpp:178 | Never confirmed against the vendored cpp-httplib header; if that version's PATCH overload differs, the PATCH tests won't compile | Grep the actual vendored `httplib.h` for the `Patch` signature (or build) before finalizing |
| Assume CMake needs no change | Plan relied on the test target already linking `::core` + `GTest::gtest_main` and `gtest_discover_tests` auto-registering new `TEST_F` cases | True per `test/CMakeLists.txt` at read time, but the plan never ran `cmake`/`ctest` to confirm the new cases build and register | Read CMakeLists to support the claim, but verify by building; "auto-registers, no CMake change" is unverified until a run |
| State the new-case count without recounting | Plan prose said "eight" in one place and "11 new cases" in another | It actually lists 10 new `TEST_F` cases — internally inconsistent count | Count `^TEST_F` blocks explicitly (`grep -cE "^TEST_F"`); never carry a prose count forward unrecounted |
| Declare the plan verified from reading source | Return shapes read from `store.cpp`/`routes.cpp`; build commands written but not run | Reading is not running — overloads, auto-registration, and compilation were never exercised | Run `cmake --preset debug && cmake --build --preset debug && ctest --preset debug` before claiming verification; until then mark `unverified` |

## Results & Parameters

### Return-shape reference (copy-paste)

```text
POST /v1/agents/{id}/start   → 200 {"status":"online","id":<id>}     (bare, NO "agent" wrapper)
POST /v1/agents/{id}/stop    → 200 {"status":"offline","id":<id>}    (bare, NO "agent" wrapper)
GET  /v1/agents/{name}       → 200 {"agent": <agent>}                (store returns bare; route wraps)
PATCH /v1/agents/{id}        → 200 {"agent": <result>}               (store returns bare; route wraps)
POST /v1/agents              → 201 {"id":<id>,"agent": <agent>}
POST /v1/agents/docker       → 201 {"id":<id>,"agent": <agent>}      (same shape as POST /v1/agents)
create_agent initial status  → "offline"  (a start test must POST /start before asserting "online")
```

### Build/run commands the plan proposed but did NOT execute

```bash
cmake --preset debug
cmake --build --preset debug
ctest --preset debug
```

Running these is the line between `unverified` and `verified-local`. Until they pass:
the `httplib::Client::Patch(path, body, type)` overload, the gtest auto-registration, and
the actual new-case count remain unconfirmed.

### Pre-plan checklist for "add route/handler tests from a follow-up issue"

```text
1. ls/Glob the cited test file path      → does it exist? what's the real path?
2. grep the handler in src/store.cpp     → what does the store return (bare? wrapped)?
3. grep the handler in src/routes.cpp    → does the route re-wrap the store value?
4. build a per-handler shape table       → assert the ACTUAL shape, not a uniform wrapper
5. grep the vendored client header       → does the overload you rely on exist?
6. read test/CMakeLists.txt              → is auto-registration real? (then BUILD to confirm)
7. grep -cE "^TEST_F"                     → recount; do not carry a prose count
8. RUN cmake/build/ctest                 → only then call the plan "verified"
```

### Context (ProjectAgamemnon issue #316)

Task: plan route-handler test coverage for ProjectAgamemnon agent routes.

- Issue said the test file was `test/test_routes.cpp`; Glob found `test/src/test_routes.cpp`.
- Highest-risk assumption: a uniform `{"agent": …}` response wrapper. Reality: `start`/`stop`
  return the bare `{"status","id"}` body; only `get_agent_by_name`/`update_agent` wrap.
- Unverified reliances handed to the reviewer: the `httplib::Client::Patch` 3-arg overload
  (inferred from `Put` at line 178), gtest auto-registration via `gtest_discover_tests` (no
  CMake change needed), and the new-case count (prose said "eight"/"11"; actual is 10).
- Plan was NOT built or run — `verification: unverified`.

### Related skills

- `cpp-cmake-ci-build-and-test-fixes` — the GTest/ctest build-and-run mechanics (CMake
  presets, `gtest_discover_tests`, linking `::core`). This skill is the complementary
  planning-discipline lesson: verify the return-shapes/paths/overloads BEFORE asserting,
  then use that skill to actually build and run.
- `planning-test-coverage-verify-premise-and-mock-targets` — sibling "verify the test
  premise against source" discipline, in the Python/mock-target context.
- `planning-follow-up-issue-line-number-drift` — re-verify cited line numbers against
  current HEAD; complementary for follow-up issues specifically.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectAgamemnon | Issue #316 — route-test planning for agent handlers | unverified — plan only; return shapes read from `src/store.cpp`/`src/routes.cpp`, but no `cmake`/`ctest` build was run |
