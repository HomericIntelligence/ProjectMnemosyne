---
name: natsc-fetchcontent-cpp20-integration
description: "Integrate nats.c into C++20 projects via CMake FetchContent without polluting ctest or leaking -Werror. Use when: (1) adding NATS JetStream pub/sub to a C++20 service, (2) natsc FetchContent is registering 300+ ctest entries, (3) check_cpp.cpp fails with -Wunused-parameter, (4) debugging nats.c API signature mismatches in C++."
category: tooling
date: 2026-04-24
version: "2.0.0"
user-invocable: false
verification: verified-ci
history: natsc-fetchcontent-cpp20-integration.history
tags:
  - nats
  - cmake
  - fetchcontent
  - cpp20
  - jetstream
  - build-testing
  - werror
  - ctest
---

# nats.c FetchContent C++20 Integration

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-24 |
| **Objective** | Add NATS JetStream support to C++20 services via nats.c FetchContent without polluting ctest with 300+ natsc tests or leaking -Werror into natsc's own test code |
| **Outcome** | Successful — CI green on ProjectKeystone PRs #272 and #198; nats_static links correctly, ctest clean |
| **Verification** | verified-ci |
| **History** | [changelog](./natsc-fetchcontent-cpp20-integration.history) |

## When to Use

- Adding NATS JetStream messaging to any C++20 project in the HomericIntelligence ecosystem
- `ctest -R` shows 300+ test entries from natsc (all requiring a live NATS server)
- CI fails with `check_cpp.cpp: error: unused parameter [-Werror,-Wunused-parameter]`
- Setting `NATS_BUILD_TESTS OFF` did not stop natsc tests from being compiled and registered
- Creating JetStream streams and durable pull consumers from C++
- Publishing JSON events to NATS subjects from a cpp-httplib REST server
- Debugging nats.c API compilation errors in C++20 code

## Verified Workflow

### Quick Reference

```cmake
# In CMakeLists.txt — add BEFORE your executable target
FetchContent_Declare(
  natsc
  GIT_REPOSITORY https://github.com/nats-io/nats.c.git
  GIT_TAG v3.12.0
  GIT_SHALLOW TRUE
)
set(NATS_BUILD_STREAMING OFF CACHE BOOL "" FORCE)
set(NATS_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(NATS_BUILD_TESTS OFF CACHE BOOL "" FORCE)
# natsc's test/ and test/check_cpp/ check BUILD_TESTING; turn it off so
# natsc's own tests are not compiled or registered with ctest.
# Also clear COMPILE_OPTIONS so our -Werror does not propagate into natsc subdirs.
set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
get_directory_property(_saved_compile_options COMPILE_OPTIONS)
set_directory_properties(PROPERTIES COMPILE_OPTIONS "")
FetchContent_MakeAvailable(natsc)
set_directory_properties(PROPERTIES COMPILE_OPTIONS "${_saved_compile_options}")
# Restore BUILD_TESTING for the rest of the project
set(BUILD_TESTING ON CACHE BOOL "" FORCE)

# Link to your target
target_link_libraries(my_target PRIVATE nats_static)
```

```cpp
// Include — NOT <nats/nats.h>, just:
#include "nats.h"
```

### Root Cause

natsc's `CMakeLists.txt` unconditionally calls `add_subdirectory(test/)` and
`add_subdirectory(test/check_cpp/)`. These subdirectories only check `BUILD_TESTING`
(the standard CMake variable) — NOT the natsc-specific `NATS_BUILD_TESTS` flag.
Setting `NATS_BUILD_TESTS OFF` does nothing to prevent those subdirectories from
being processed and their tests registered with ctest.

Additionally, `add_compile_options()` at the CMake directory level propagates into
FetchContent subdirectories. So any `-Werror` in your project's global compile
options leaks into natsc's `test/check_cpp/check_cpp.cpp`, which has
`-Wunused-parameter` violations, breaking the build.

The fix requires BOTH:
1. `BUILD_TESTING OFF` — stops natsc's subdirs from registering tests with ctest
2. `set_directory_properties(PROPERTIES COMPILE_OPTIONS "")` — clears propagated
   `-Werror` before `FetchContent_MakeAvailable`, then restores your flags after

### Detailed Steps

1. Add `FetchContent_Declare` for natsc (see Quick Reference)
2. Set `NATS_BUILD_STREAMING OFF`, `NATS_BUILD_EXAMPLES OFF`, `NATS_BUILD_TESTS OFF`
3. Save current `COMPILE_OPTIONS` using `get_directory_property`
4. Set `BUILD_TESTING OFF` (controls natsc's test/ subdir inclusion)
5. Clear `COMPILE_OPTIONS` on the current directory to zero
6. Call `FetchContent_MakeAvailable(natsc)` — natsc now sees no warning flags and BUILD_TESTING=OFF
7. Restore `COMPILE_OPTIONS` immediately after
8. Restore `BUILD_TESTING ON` so your own tests still register with ctest
9. Use `nats_static` target (static link avoids runtime dep)
10. Include `"nats.h"` (not `<nats/nats.h>`) — the target sets include dirs automatically
11. Requires `libssl-dev` at build time (nats.c uses OpenSSL for TLS)

### JetStream Stream Creation (C++)

```cpp
jsCtx* js = nullptr;
natsConnection_JetStream(&js, conn, nullptr);

jsStreamConfig cfg;
jsStreamConfig_Init(&cfg);
cfg.Name = "homeric-myrmidon";
const char* subjects[] = {"hi.myrmidon.>"};
cfg.Subjects = subjects;
cfg.SubjectsLen = 1;

jsStreamInfo* si = nullptr;
jsErrCode jerr = static_cast<jsErrCode>(0);  // CRITICAL: C enum needs cast in C++
natsStatus s = js_AddStream(&si, js, &cfg, nullptr, &jerr);
// Ignore "already exists" errors — idempotent
if (s == NATS_OK && si) jsStreamInfo_Destroy(si);
```

### JetStream Publish (C++)

```cpp
jsPubAck* pa = nullptr;
jsErrCode jerr = static_cast<jsErrCode>(0);
natsStatus s = js_Publish(&pa, js, subject.c_str(),
                          payload.c_str(), payload.size(),
                          nullptr, &jerr);
if (s == NATS_OK && pa) jsPubAck_Destroy(pa);
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `#include <nats/nats.h>` | Standard angle-bracket include | nats.c installs headers flat, not in nats/ subdirectory | Use `#include "nats.h"` — the CMake target sets include dirs |
| `js_AddStream(&si, js, &cfg, nullptr, nullptr)` | Passing nullptr for jsErrCode | Requires `jsErrCode*` parameter, nullptr causes segfault in some builds | Always pass `&jerr` with `jsErrCode jerr = static_cast<jsErrCode>(0)` |
| `jsErrCode jerr = 0` | Direct int initialization | `jsErrCode` is a C enum — C++ doesn't allow implicit int→enum conversion | Use `static_cast<jsErrCode>(0)` in C++20 |
| `NATS_BUILD_STREAMING ON` | Default streaming support | Adds unnecessary STAN dependency, increases build time | Set `NATS_BUILD_STREAMING OFF` — JetStream is built-in, STAN is separate |
| `NATS_BUILD_TESTS OFF` only | Set natsc-specific flag to suppress tests | natsc's CMakeLists adds `test/` subdirs unconditionally; those subdirs only check `BUILD_TESTING`, not `NATS_BUILD_TESTS` | Must set `BUILD_TESTING OFF` (the standard CMake variable) to actually suppress natsc's tests |
| `BUILD_TESTING OFF` without clearing COMPILE_OPTIONS | Fixed the 300 test registrations but left -Werror in place | natsc's `test/check_cpp/check_cpp.cpp` still got compiled with `-Werror` from project-level `add_compile_options`, failing with `-Wunused-parameter` | Must also clear COMPILE_OPTIONS before FetchContent_MakeAvailable and restore after |
| Generator expression `$<$<COMPILE_LANGUAGE:CXX>:-Werror>` | Scoped -Werror to C++ translation units only | Does not prevent propagation into natsc's C files compiled by FetchContent when BUILD_TESTING is still ON | Correct for the main project's C compilation, but `BUILD_TESTING OFF` + COMPILE_OPTIONS clear is needed for the test/check_cpp subdir which is a C++ file |
| Variable save/restore for BUILD_TESTING | `set(BUILD_TESTING_SAVED ...) ... set(BUILD_TESTING "${BUILD_TESTING_SAVED}")` | Incomplete — only addressed test registration, not the -Werror propagation into check_cpp.cpp | Need the directory-properties COMPILE_OPTIONS clearing pattern alongside BUILD_TESTING management |

## Results & Parameters

```cmake
# Verified minimal FetchContent block for natsc (ProjectKeystone, CMake 3.31, Clang 18)
FetchContent_Declare(
  natsc
  GIT_REPOSITORY https://github.com/nats-io/nats.c.git
  GIT_TAG v3.12.0
  GIT_SHALLOW TRUE
)
set(NATS_BUILD_STREAMING OFF CACHE BOOL "" FORCE)
set(NATS_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(NATS_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
get_directory_property(_saved_compile_options COMPILE_OPTIONS)
set_directory_properties(PROPERTIES COMPILE_OPTIONS "")
FetchContent_MakeAvailable(natsc)
set_directory_properties(PROPERTIES COMPILE_OPTIONS "${_saved_compile_options}")
set(BUILD_TESTING ON CACHE BOOL "" FORCE)
```

```yaml
# Verified context:
project: ProjectKeystone
prs: ["#272", "#198"]
natsc_version: v3.12.0
cmake_version: "3.31"
compiler: Clang 18
os: Ubuntu 24.04
cmake_target: nats_static
requires: libssl-dev (build), libssl3 (runtime)
ctest_natsc_tests_before_fix: "300+"
ctest_natsc_tests_after_fix: 0
ci_result: all green (asan, tsan, ubsan presets)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectKeystone | CI builds with nats.c v3.12.0 FetchContent | PRs #272 and #198 — asan/tsan/ubsan all passed |
| ProjectAgamemnon | E2E pipeline implementation (v1.0.0 approach, v3.9.1) | C++20 REST server with 20+ routes + NATS event publishing |
| ProjectNestor | E2E pipeline implementation (v1.0.0 approach, v3.9.1) | C++20 research stats server with NATS research event publishing |
| hello-myrmidon | E2E pipeline implementation (v1.0.0 approach, v3.9.1) | Standalone C++20 NATS pull consumer worker |

## See Also

- [`cmake-cxx-warnings-fetchcontent-c-lib`](./cmake-cxx-warnings-fetchcontent-c-lib.md) — Generator-expression approach to scope -Werror to C++ only (complementary fix for the main project's C compilation)
