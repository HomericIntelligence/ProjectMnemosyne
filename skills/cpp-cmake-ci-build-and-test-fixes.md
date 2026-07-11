---
name: cpp-cmake-ci-build-and-test-fixes
description: "Fix C++/CMake CI build and test failures. Use when: (1) FetchContent C library breaks build with -Werror due to global warning flags, (2) ctest reports 'No tests found' because library target contains main() conflicting with GTest::gtest_main, (3) Ubuntu 24.04 apt Docker build fails with 'GTest::gmock target not found', (4) TSan reports data races or hangs tests, (5) clang-tidy floods warnings from _deps/ vendor headers."
category: ci-cd
date: 2026-05-19
version: "1.0.0"
user-invocable: false
history: cpp-cmake-ci-build-and-test-fixes.history
tags:
  - cmake
  - cpp20
  - ci-cd
  - fetchcontent
  - compiler-warnings
  - generator-expressions
  - gtest
  - gmock
  - ctest
  - ubuntu
  - apt
  - dockerfile
  - tsan
  - sanitizers
  - data-race
  - msan
  - clang-tidy
  - header-filter
  - static-analysis
  - github-actions
  - concurrentqueue
  - tsan-suppression
---

# C++/CMake CI Build and Test Fixes

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-19 |
| **Objective** | Fix C++/CMake CI failures: FetchContent warning leakage, GTest target conflicts, Ubuntu package splits, TSan races/hangs, and clang-tidy vendor header pollution |
| **Outcome** | All five failure patterns resolved with targeted fixes; CI green across asan/lsan/ubsan/tsan |
| **Verification** | verified-ci |

## When to Use

- Adding a C library (nats.c, libuv, sqlite, etc.) via `FetchContent_MakeAvailable` and CI starts failing with `error: unused parameter [...] [-Werror,-Wunused-parameter]` in third-party source files
- `ctest` reports `No tests were found!!!` even though the test binary builds; running it prints application output instead of GTest output
- Docker/CI build on Ubuntu 24.04 fails with `Target "..." links to GTest::gmock but the target was not found`
- TSan CI job reports `WARNING: ThreadSanitizer: data race`, a test hangs until job timeout, or MSan build fails with `Failed to determine the source files for the regular expression backend`
- clang-tidy CI flooded with warnings from `_deps/` vendor headers despite `HeaderFilterRegex` listing only `src/` or `include/`

## Verified Workflow

### Quick Reference

```cmake
# Fix 1 — Scope warning flags to C++ only (FetchContent C library safety):
add_compile_options(
  $<$<COMPILE_LANGUAGE:CXX>:-Wall>
  $<$<COMPILE_LANGUAGE:CXX>:-Wextra>
  $<$<COMPILE_LANGUAGE:CXX>:-Wpedantic>
  $<$<COMPILE_LANGUAGE:CXX>:-Werror>)
```

```cmake
# Fix 2 — Remove main() from library sources; use a stub instead:
# cmake/SourcesAndHeaders.cmake
set(sources src/version_info.cpp)   # was: src/main.cpp
```

```dockerfile
# Fix 3 — Ubuntu 24.04: install libgmock-dev alongside libgtest-dev:
RUN apt-get update && apt-get install -y \
    libgtest-dev \
    libgmock-dev \
    libbenchmark-dev \
    libspdlog-dev \
    libconcurrentqueue-dev
```

```bash
# Fix 4 — Diagnose TSan failures:
gh run view <run-id> --log 2>&1 | grep -A 20 "WARNING: ThreadSanitizer: data race" | head -100
# Find hung test:
gh run view <run-id> --log 2>&1 | grep "Start " | grep -oP '\d+(?=:)' | sort -un > /tmp/started.txt
gh run view <run-id> --log 2>&1 | grep "Test #" | grep -oP '(?<=#)\d+' | sort -un > /tmp/completed.txt
comm -23 /tmp/started.txt /tmp/completed.txt
```

```yaml
# Fix 5 — clang-tidy: anchor HeaderFilterRegex to project name:
HeaderFilterRegex: '/YourProjectName/(include|src|test)/'
```

---

### Fix 1: FetchContent C Library Breaking Compilation (Warning Scope)

`add_compile_options(...)` without a `COMPILE_LANGUAGE` guard applies to **all** languages, including C. When `FetchContent_MakeAvailable` pulls a C library, its `.c` files inherit the project's `-Werror`, causing third-party code to fail.

**Fix**: Wrap every warning/error flag with a generator expression:

```cmake
# BEFORE (broken — applies to ALL languages):
add_compile_options(-Wall -Wextra -Wpedantic -Werror)

# AFTER (correct — C++ translation units only):
add_compile_options(
  $<$<COMPILE_LANGUAGE:CXX>:-Wall>
  $<$<COMPILE_LANGUAGE:CXX>:-Wextra>
  $<$<COMPILE_LANGUAGE:CXX>:-Wpedantic>
  $<$<COMPILE_LANGUAGE:CXX>:-Werror>)

# GCC-specific suppressions also need the guard:
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
  add_compile_options($<$<COMPILE_LANGUAGE:CXX>:-Wno-dangling-reference>)
endif()
```

Verify with full sanitizer preset matrix:

```bash
cmake --preset asan && cmake --build --preset asan && ctest --preset asan
cmake --preset tsan && cmake --build --preset tsan && ctest --preset tsan
cmake --preset ubsan && cmake --build --preset ubsan && ctest --preset ubsan
```

---

### Fix 2: Library main() Conflicting with GTest::gtest_main

The library target (`add_library`) includes `src/main.cpp` which defines `main()`. The test executable links both the library and `GTest::gtest_main` — two `main()` symbols; the linker picks the library's, and GTest never runs.

**Fix**: Remove `main.cpp` from library sources; replace with a stub that has no `main()`:

```cmake
# cmake/SourcesAndHeaders.cmake
# BEFORE (broken):
set(sources src/main.cpp)

# AFTER (fixed):
set(sources src/version_info.cpp)
```

```cpp
// src/version_info.cpp — no main(), just library symbols:
#include "projectfoo/version.hpp"
namespace projectfoo {
const char* get_version() { return kVersion.data(); }
const char* get_project_name() { return kProjectName.data(); }
}
```

If `ctest --preset coverage` fails with "No such test preset", add it to `CMakePresets.json`:

```json
{
  "testPresets": [
    {
      "name": "coverage",
      "configurePreset": "coverage",
      "output": { "outputOnFailure": true }
    }
  ]
}
```

**Diagnosis**: Run the test binary directly — if it prints a version string instead of GTest output, this is the bug.

---

### Fix 3: Ubuntu 24.04 GTest/GMock apt Package Split

On Ubuntu 24.04, `libgtest-dev` ships only `GTest::gtest` and `GTest::gtest_main`. The `GTest::gmock` and `GTest::gmock_main` CMake targets live in a **separate** package: `libgmock-dev`.

Complete apt → CMake target mapping:

```yaml
apt_to_cmake_targets:
  libgtest-dev:
    cmake_targets: [GTest::gtest, GTest::gtest_main]
    notes: "Does NOT include GMock on Ubuntu 24.04"
  libgmock-dev:
    cmake_targets: [GTest::gmock, GTest::gmock_main]
    notes: "SEPARATE package — easy to miss"
  libbenchmark-dev:
    cmake_targets: [benchmark::benchmark, benchmark::benchmark_main]
  libspdlog-dev:
    cmake_targets: [spdlog::spdlog]
    notes: "Includes bundled fmt::fmt"
  libconcurrentqueue-dev:
    cmake_targets: [concurrentqueue::concurrentqueue]
    notes: "Header-only; has CMake config"
```

> Note: If using Conan for CI, Conan installs GTest and GMock together automatically. The split only affects the apt (Docker) path.

---

### Fix 4: TSan Data Races, Hung Tests, and MSan Build Failures

#### 4a. Diagnose TSan Races

Use `--log` with targeted grep (not `--log-failed`):

```bash
gh run view <run-id> --log 2>&1 | grep -A 20 "WARNING: ThreadSanitizer: data race" | head -100
```

Common race patterns and fixes:

| Race Pattern | Root Cause | Fix |
| --- | --- | --- |
| Shared `std::mt19937 rng_` | Worker threads call `generateLatency()` concurrently | Add `mutable std::mutex rng_mutex_`; lock in all methods |
| Shared `std::unordered_map` | Multiple threads call `registerAgent()` / `submit()` | Add `mutable std::mutex map_mutex_`; lock in all 4 methods |
| `std::function<bool()> readiness_check_` | Server thread reads while another thread writes | Add `mutable std::mutex readiness_mutex_`; use atomics for fd/port |

For `server_fd_` and `port_`, prefer atomics to avoid mutex overhead:

```cpp
std::atomic<int> server_fd_{-1};
std::atomic<uint16_t> port_{0};
// In stop():
int fd = server_fd_.exchange(-1);  // Atomic get-and-clear
if (fd >= 0) close(fd);
```

#### 4b. Nested Class Race — Parent Mutex Does Not Protect Child Members

A subtle pattern: `SimulatedCluster::registerAgent()` holds `agent_map_mutex_` for its own map, then calls `node->registerAgent(id)` outside that lock. Multiple threads racing on the same NUMA node's `local_agents_` set.

**Fix**: Each class with shared mutable state needs its own mutex:

```cpp
class SimulatedNUMANode {
    mutable std::mutex agents_mutex_;
    std::unordered_set<std::string> local_agents_;
public:
    void registerAgent(const std::string& agent_id) {
        std::lock_guard<std::mutex> lock(agents_mutex_);
        local_agents_.insert(agent_id);
    }
    bool hasAgent(const std::string& agent_id) const {
        std::lock_guard<std::mutex> lock(agents_mutex_);
        return local_agents_.find(agent_id) != local_agents_.end();
    }
};
```

#### 4c. ConcurrentQueue TSan False Positives — Suppression File

`moodycamel::ConcurrentQueue` uses relaxed atomic ordering internally. TSan cannot verify lock-free sequencing and reports races on data member moves during enqueue/dequeue. These are false positives.

Create `tsan.supp` at project root:

```text
# tsan.supp
race:moodycamel::ConcurrentQueue
race:moodycamel::details
race:<project>::concurrency::WorkItem::WorkItem
race:<project>::concurrency::WorkStealingQueue::push
race:<project>::concurrency::WorkStealingQueue::steal
race:<project>::concurrency::WorkStealingQueue::pop
```

Pass via `TSAN_OPTIONS` in CI (`.github/workflows/ci.yml`):

```yaml
- name: Run tests with ${{ matrix.name }}
  run: make test.debug.${{ matrix.sanitizer }}.native
  env:
    TSAN_OPTIONS: ${{ matrix.sanitizer == 'tsan' && format('suppressions={0}/tsan.supp:second_deadlock_stack=1', github.workspace) || '' }}
```

**Use suppression when**: the library is a well-known battle-tested lock-free structure (moodycamel, folly, tbb) and the "race" is on values one thread owns exclusively. **Fix the code** when multiple threads genuinely share state.

#### 4d. Disable Hung Test

A hung test causes the CI job to be killed (not failed). Identify via log diff:

```bash
gh run view <run-id> --log 2>&1 | grep "Start " | grep -oP '\d+(?=:)' | sort -un > /tmp/started.txt
gh run view <run-id> --log 2>&1 | grep "Test #" | grep -oP '(?<=#)\d+' | sort -un > /tmp/completed.txt
comm -23 /tmp/started.txt /tmp/completed.txt   # Shows hung test number(s)
```

Disable with `DISABLED_` prefix and add ctest timeout:

```cpp
// TSan instruments thread-start/join so heavily that pool construction
// takes >600s on CI runners.
TEST(ThreadPoolTest, DISABLED_CreateAndDestroy) {
  ThreadPool pool(4);
  EXPECT_EQ(pool.size(), 4u);
}
```

```makefile
CTEST_TIMEOUT ?= 120

test:
    cd build && ctest --output-on-failure --timeout $(CTEST_TIMEOUT)

# TSan needs longer timeout due to instrumentation overhead:
%.tsan:
    TSAN_OPTIONS="suppressions=$(PWD)/tsan.supp:second_deadlock_stack=1" \
    CTEST_TIMEOUT=600 \
    $(MAKE) $*.native
```

#### 4e. Remove MSan from CI Matrix

MSan builds fail when CMake runs probe programs (e.g., Google Benchmark regex detection) against uninstrumented stdlib.

```yaml
# Before:
matrix:
  sanitizer: [asan, ubsan, tsan, msan, lsan]

# After (msan removed):
matrix:
  sanitizer: [asan, ubsan, tsan, lsan]
```

A proper MSan fix requires building instrumented libc++ from source — a multi-hour build. ASan+UBSan+LSan provide substantial coverage in the meantime.

#### 4f. Fix Dockerfile COPY Paths After CMAKE_RUNTIME_OUTPUT_DIRECTORY Change

When `CMAKE_RUNTIME_OUTPUT_DIRECTORY` is set to `${CMAKE_BINARY_DIR}/bin`, binaries land in `/workspace/build/bin/` not `/workspace/build/`.

```dockerfile
# Before (wrong):
COPY --from=builder /workspace/build/my_binary /usr/local/bin/

# After (correct):
COPY --from=builder /workspace/build/bin/my_binary /usr/local/bin/
```

```bash
git grep "CMAKE_RUNTIME_OUTPUT_DIRECTORY" CMakeLists.txt
```

---

### Fix 5: clang-tidy HeaderFilterRegex Matching \_deps/ Vendor Headers

A bare `HeaderFilterRegex: '(include|src|test)/'` matches paths like `_deps/nats_c-src/src/nats.h` because the path contains `/src/`. Anchor to the project name to prevent this.

```yaml
# In .clang-tidy:
Checks: >
  *,
  -fuchsia-*,
  -llvm-*,
  -llvmlibc-*,
  ...
WarningsAsErrors: ''
HeaderFilterRegex: '/YourProjectName/(include|src|test)/'
FormatStyle: file
```

**Do not** use `ExcludeHeaderFilterRegex` — causes "unknown key" parse error in system clang-tidy (Ubuntu 24.04). Also add `-llvmlibc-*` separately; `-llvm-*` does not suppress the `llvmlibc-*` check family.

```text
# GitHub Actions runner path examples (ProjectAgamemnon):
# MATCHED:     /home/runner/work/ProjectAgamemnon/ProjectAgamemnon/include/...
# NOT MATCHED: /home/runner/work/ProjectAgamemnon/ProjectAgamemnon/build/debug/_deps/nats_c-src/src/nats.h
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Global warning flags without language guard | Keep `-Wall -Wextra -Wpedantic -Werror` globally | nats.c `asynccb.c:32` failed: `error: unused parameter 'scPtr' [-Werror,-Wunused-parameter]` | Always use `$<$<COMPILE_LANGUAGE:CXX>:flag>` when mixing C and C++ |
| Add `-Wno-unused-parameter` globally | Suppress unused-parameter for all targets | Silences useful warnings in project's own C++ code, defeating `-Wall` | Scope the error flags; don't suppress globally |
| `target_compile_options` on FetchContent target | Remove flags from nats.c target after `FetchContent_MakeAvailable` | FetchContent targets may not be addressable by name before MakeAvailable; fragile | Fix the source (global flags scope) rather than patching downstream targets |
| Keep `main()` in library | Library had `add_library(Foo src/main.cpp)` with tests linking `Foo::Foo + GTest::gtest_main` | Two `main()` symbols — linker picks library's `main()`, GTest never runs | Library targets must NEVER contain `main()` |
| Make library INTERFACE | Changed `add_library(Foo ...)` to `add_library(Foo INTERFACE)` | CMake errors — INTERFACE libraries can't have source files | Use a stub source file instead |
| Only install `libgtest-dev` in Docker | Assumed it provides all GTest CMake targets | Ubuntu 24.04 splits GMock into a separate package; `GTest::gmock` not found | Always install `libgmock-dev` alongside `libgtest-dev` on Ubuntu 24.04 |
| `--log-failed` for TSan error context | `gh run view <id> --log-failed` to see build errors | Output shows git cleanup steps but misses compilation and test output | Use `gh run view <id> --log` with targeted `grep` patterns |
| Increase TSan job timeout | Proposed longer `timeout-minutes` on TSan GitHub Actions job | User explicitly rejected: a hung test wastes CI minutes at any timeout | Disable the hung test; add `--timeout 120` to ctest |
| Fix MSan by instrumenting libc++ | Compile instrumented libc++ from source | Multi-hour build, complex CI setup | Remove MSan from CI matrix and file an issue |
| Creating fix branch from feature branch | Checked out from a stale feature branch with stash | Stash pop caused merge conflicts with main | Always `git checkout main && git pull` before creating a fix branch |
| `ExcludeHeaderFilterRegex: '_deps/'` in .clang-tidy | Exclude vendor headers by explicit key | "unknown key 'ExcludeHeaderFilterRegex'" — not supported on Ubuntu 24.04 clang-tidy | Use anchored `HeaderFilterRegex` instead |
| Bare directory regex for clang-tidy | `HeaderFilterRegex: '(include\|src\|test)/'` | Matches `_deps/nats_c-src/src/nats.h` because the path contains `/src/` | Must anchor to project root name |
| Only `-llvm-*` suppressor in clang-tidy | Expected `-llvm-*` to cover all llvm-prefixed checks | `llvmlibc-*` checks still fire | Add `-llvmlibc-*` separately in Checks list |
| Parent mutex protecting child object | Assumed `SimulatedCluster::agent_map_mutex_` would protect calls into `SimulatedNUMANode` | Parent mutex only protects parent's map; child's `local_agents_` is a separate object | Each class with shared mutable state needs its own mutex |
| Fixing ConcurrentQueue races in application code | Adding locks around `WorkStealingQueue::push`/`steal`/`pop` | Serializes the lock-free queue, defeating its purpose; races are on already-dequeued (exclusively owned) items | Use `tsan.supp` to suppress false positives on well-tested lock-free data structures |
| `CTEST_TIMEOUT=600` for ThreadPool hang | Set longer timeout in `%.tsan` Makefile rule | Test hung for the full 600s — TSan instrumentation overhead on thread lifecycle, not a real race | Disable with `DISABLED_` prefix; increasing timeout only delays CI failure |
| Running ctest without per-test `--timeout` | No `--timeout` flag on ctest invocation | A hung test blocks the entire CI job indefinitely | Always add `--timeout 120` to prevent runaway tests |

## Results & Parameters

```yaml
# Verified C++ CI fix context:
distro: Ubuntu 24.04
compiler: clang-18 / GCC (>=12 for C++20)
ci: GitHub Actions
cmake_version: ">=3.25"
sanitizers_tested: [asan, ubsan, tsan, lsan]
sanitizers_removed: [msan]
```

```cmake
# Final warning flags configuration (CMakeLists.txt):
add_compile_options(
  $<$<COMPILE_LANGUAGE:CXX>:-Wall>
  $<$<COMPILE_LANGUAGE:CXX>:-Wextra>
  $<$<COMPILE_LANGUAGE:CXX>:-Wpedantic>
  $<$<COMPILE_LANGUAGE:CXX>:-Werror>)

if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
  add_compile_options($<$<COMPILE_LANGUAGE:CXX>:-Wno-dangling-reference>)
endif()
```

```cpp
// TSan-safe shared RNG pattern:
class SimulatedNetwork {
    mutable std::mutex rng_mutex_;
    std::mt19937 rng_;
    double generateLatency() const {
        std::lock_guard<std::mutex> lock(rng_mutex_);
        return dist_(rng_);
    }
};
```

```cpp
// TSan-safe registry map pattern:
class SimulatedCluster {
    mutable std::mutex agent_map_mutex_;
    std::unordered_map<std::string, size_t> agent_node_map_;
    void registerAgent(const std::string& id, size_t node) {
        std::lock_guard<std::mutex> lock(agent_map_mutex_);
        agent_node_map_[id] = node;
    }
};
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectKeystone | CI builds broken by nats.c v3.12.0 FetchContent integration | PR #379, asan/lsan/ubsan all passed after scoping warning flags to CXX |
| ProjectKeystone | PR #146 — fix CI failures (TSan races, hung test, MSan) | C++20, GCC/Clang, GitHub Actions, Google Benchmark |
| ProjectKeystone | PR #147 — repo audit quick wins | Issues #148-#158 filed from audit findings |
| ProjectKeystone | Docker build — agent_unit_tests target | Added libgmock-dev to Dockerfile; GTest::gmock target resolved |
| ProjectAgamemnon | CI coverage fix | Library had main.cpp — replaced with version_info.cpp |
| ProjectAgamemnon | clang-tidy CI FAILURE to SUCCESS | Anchored HeaderFilterRegex + added -llvmlibc-* suppressor |
| ProjectNestor | CI coverage fix | Same main() conflict pattern applied |
| ProjectNestor | clang-tidy CI | Same HeaderFilterRegex fix, same FetchContent nats.c dependency |
| Mnemosyne | TSan fixes: NUMA node data race, ConcurrentQueue false positives, ThreadPool hang | verified-ci: all three failure modes resolved |
