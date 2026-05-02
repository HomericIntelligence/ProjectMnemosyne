---
name: conan-hybrid-cpp20-turnkey-packaging
description: "Hybrid Conan 2.x + FetchContent packaging for C++20 CMake repos with E2E install validation. Use when: (1) migrating a FetchContent-only project to Conan, (2) some deps aren't on ConanCenter so you need both, (3) integrating Conan with CMakePresets.json, (4) validating installed packages work end-to-end across a multi-repo ecosystem."
category: tooling
date: 2026-04-07
version: "1.2.0"
user-invocable: false
verification: verified-local
history: conan-hybrid-cpp20-turnkey-packaging.history
tags:
  - conan
  - cmake
  - fetchcontent
  - cpp20
  - packaging
  - e2e
  - pip
  - docker
---

# Hybrid Conan 2.x + FetchContent for C++20 CMake Projects

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-07 |
| **Objective** | Migrate C++20 CMake repos from pure FetchContent to hybrid Conan + FetchContent, then validate installed packages work end-to-end |
| **Outcome** | Successful — 4 C++ repos (Agamemnon, Nestor, Charybdis, Keystone) build and test with hybrid deps; E2E install validation scripts created |
| **Verification** | verified-local |
| **History** | [changelog](./conan-hybrid-cpp20-turnkey-packaging.history) |

## When to Use

- Migrating a C++20 CMake project from FetchContent-only to Conan for binary caching and faster rebuilds
- A dependency is not reliably on ConanCenter (e.g., nats.c, cista) but others are (cpp-httplib, nlohmann_json, gtest, spdlog, concurrentqueue)
- Integrating Conan 2.x with CMakePresets.json (v8) — getting the toolchainFile path right
- Complex FetchContent migration with 6+ deps where some must stay as FetchContent
- Validating that Conan-exported packages can be consumed by downstream projects
- Building a meta-repo `just install` that deploys all C++ binaries/libraries to a prefix
- Creating E2E Docker compose stacks that build C++ services from source alongside Python services

## Verified Workflow

### Quick Reference

```bash
# Single repo: build with Conan
conan install . --output-folder=build/debug --profile=conan/profiles/debug --build=missing
cmake --preset debug
cmake --build --preset debug
ctest --preset debug

# Meta-repo: build all + install
just build
just install PREFIX=/tmp/staging

# E2E validation
just e2e-conan-validate   # Conan export → consumer → cmake install
just e2e-pip-validate     # Python packages in clean venvs
just e2e-full             # Docker E2E + Conan + pip
```

### Step 1: Create conanfile.py (Conan deps only)

```python
from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMakeDeps

class ProjectFooConan(ConanFile):
    name = "projectfoo"
    version = "0.1.0"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("cpp-httplib/0.18.3")
        self.requires("nlohmann_json/3.11.3")

    def build_requirements(self):
        self.test_requires("gtest/1.14.0")

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
```

For repos with optional features (e.g., gRPC), use Conan options:

```python
class ProjectKeystoneConan(ConanFile):
    options = {"with_grpc": [True, False]}
    default_options = {"with_grpc": False}

    def requirements(self):
        self.requires("spdlog/1.12.0")
        self.requires("concurrentqueue/1.0.4")
        if self.options.with_grpc:
            self.requires("yaml-cpp/0.8.0")

    def build_requirements(self):
        self.test_requires("gtest/1.14.0")
        self.test_requires("benchmark/1.8.3")
```

### Step 2: Update CMakeLists.txt (hybrid pattern)

Replace FetchContent for Conan-managed deps with `find_package`. Keep FetchContent for deps not on ConanCenter.

```cmake
# Conan deps
find_package(GTest REQUIRED)
find_package(benchmark REQUIRED)
find_package(spdlog REQUIRED)
find_package(concurrentqueue REQUIRED)
include(GoogleTest)

# FetchContent deps (not on ConanCenter)
include(FetchContent)
FetchContent_Declare(cista
  GIT_REPOSITORY https://github.com/felixguendling/cista.git
  GIT_TAG v0.14)
FetchContent_MakeAvailable(cista)
```

**Critical: Update include directories.** FetchContent variables like `${concurrentqueue_SOURCE_DIR}` and `${spdlog_SOURCE_DIR}/include` no longer exist. Remove them from `target_include_directories` and use target-based linking instead:

```cmake
# BEFORE (FetchContent)
target_include_directories(mylib PUBLIC
    $<BUILD_INTERFACE:${concurrentqueue_SOURCE_DIR}>
  PRIVATE
    $<BUILD_INTERFACE:${spdlog_SOURCE_DIR}/include>)
target_link_libraries(mylib PRIVATE spdlog)

# AFTER (Conan)
target_link_libraries(mylib
    PUBLIC concurrentqueue::concurrentqueue
    PRIVATE spdlog::spdlog)
# No include_directories needed — Conan targets propagate includes automatically
```

### Step 3: Add toolchainFile to CMakePresets.json

```json
{
  "name": "base",
  "hidden": true,
  "generator": "Ninja",
  "binaryDir": "${sourceDir}/build/${presetName}",
  "toolchainFile": "${sourceDir}/build/${presetName}/conan_toolchain.cmake"
}
```

### Step 4: Replace FetchContent(gtest) namespace aliases

The GTest namespace aliases block is unnecessary with Conan — Conan's gtest package provides `GTest::gtest`, `GTest::gtest_main`, `GTest::gmock`, `GTest::gmock_main` natively. Delete the entire alias block:

```cmake
# DELETE THIS ENTIRE BLOCK — Conan provides these targets natively
if(NOT TARGET GTest::gtest)
  add_library(GTest::gtest ALIAS gtest)
endif()
# ... etc
```

### Step 5: Meta-repo orchestration (Odysseus pattern)

The meta-repo justfile delegates to each submodule's build system with a `BUILD_ROOT` override:

```just
BUILD_ROOT := justfile_directory() / "build"

_build-keystone:
    cd provisioning/ProjectKeystone && pixi run conan install . \
        --output-folder="{{BUILD_ROOT}}/ProjectKeystone" \
        --profile=conan/profiles/debug \
        --build=missing
    cmake -S provisioning/ProjectKeystone -B "{{BUILD_ROOT}}/ProjectKeystone" \
        -DCMAKE_TOOLCHAIN_FILE="{{BUILD_ROOT}}/ProjectKeystone/conan_toolchain.cmake" \
        -DCMAKE_BUILD_TYPE=Debug -G Ninja
    cmake --build "{{BUILD_ROOT}}/ProjectKeystone"

install PREFIX="/usr/local":
    cmake --install "{{BUILD_ROOT}}/ProjectAgamemnon" --prefix "{{PREFIX}}"
    cmake --install "{{BUILD_ROOT}}/ProjectNestor" --prefix "{{PREFIX}}"
    cmake --install "{{BUILD_ROOT}}/ProjectKeystone" --prefix "{{PREFIX}}"
```

### Step 6: E2E Conan install validation

Create a consumer project that validates all packages can be exported, installed, and consumed:

```bash
# Export each C++ repo to local Conan cache
conan export control/ProjectAgamemnon
conan export provisioning/ProjectKeystone

# Build a consumer that find_package()s them all
conan install e2e/conan-consumer --output-folder=build --build=missing
cmake -S e2e/conan-consumer -B build -DCMAKE_TOOLCHAIN_FILE=build/conan_toolchain.cmake
cmake --build build
./build/validate_install  # Should print success
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `cmake_layout(self)` in conanfile.py | Used Conan's cmake_layout for automatic output paths | Creates nested `build/Debug/generators/` that doesn't match CMakePresets `build/${presetName}` convention | Remove `cmake_layout()` — use explicit `--output-folder`. Generators land directly in the specified directory. |
| Stale CMakeCache after migration | Configured CMake with FetchContent, then added Conan toolchain | Old CMakeCache.txt ignores `CMAKE_TOOLCHAIN_FILE` — CMake warns "Manually-specified variables were not used" | Always delete `build/` before first Conan build. Stale FetchContent cache silently ignores the Conan toolchain. |
| Full Conan replacement for nats.c | Tried `cnats` Conan package for nats.c | cnats availability/version uncertain on ConanCenter — risk of mismatch | Hybrid approach: Conan for well-supported packages, FetchContent for niche ones |
| Keeping `${dep_SOURCE_DIR}` include paths | After switching to `find_package(concurrentqueue)`, left `${concurrentqueue_SOURCE_DIR}` in `target_include_directories` | Variable is empty — Conan deps don't set FetchContent variables | Remove all `${*_SOURCE_DIR}` include paths for Conan deps. Conan targets propagate their include dirs automatically via `target_link_libraries`. |
| `concurrentqueue/1.0.4cci.2` Conan name | Assumed ConanCenter uses `cci.2` suffix for concurrentqueue | Actual package name is `concurrentqueue/1.0.4` (no suffix) | Always verify exact package names with `conan search "pkgname/*"` before writing conanfile.py |
| Linking `yaml-cpp` directly (no namespace) | Used `target_link_libraries(... yaml-cpp)` | Conan provides `yaml-cpp::yaml-cpp` namespaced target — bare `yaml-cpp` resolves to FetchContent target which no longer exists | Always use Conan namespace pattern: `yaml-cpp::yaml-cpp`, `spdlog::spdlog`, `concurrentqueue::concurrentqueue` |
| Conan dep PRIVATE on library with public headers | Linked `spdlog::spdlog` as PRIVATE on `keystone_concurrency` which has `logger.hpp` as a public header; `concurrentqueue::concurrentqueue` linked only to `keystone_core` but not to `keystone_concurrency` whose public header `work_stealing_queue.hpp` includes it | CMake configure succeeds (targets declared), but compilation fails: `fatal error: 'spdlog/fmt/fmt.h' file not found` — PRIVATE deps don't propagate include dirs to consumers that include public headers | Use PUBLIC for any Conan dep whose types/includes appear in a PUBLIC header. PRIVATE is only correct if the dep is used exclusively in .cpp sources. Audit with: `grep -r "#include <spdlog/" include/` — any hit means PUBLIC. |

## Results & Parameters

```yaml
# Conan target name mapping (Conan namespace → use in target_link_libraries)
httplib: httplib::httplib
nlohmann_json: nlohmann_json::nlohmann_json
gtest: GTest::gtest_main
gmock: GTest::gmock
spdlog: spdlog::spdlog
concurrentqueue: concurrentqueue::concurrentqueue
benchmark: benchmark::benchmark
yaml-cpp: yaml-cpp::yaml-cpp

# FetchContent targets (not migrated — keep as-is)
nats_static: nats_static   # nats.c not on ConanCenter
cista: cista                # cista not on ConanCenter (use ${cista_SOURCE_DIR}/include)

# File changes per repo (new Conan migration)
new_files:
  - conanfile.py
  - conan/profiles/default     # Release profile
  - conan/profiles/debug       # Debug profile
  - CMakePresets.json           # If not already present
  - justfile                    # If not already present (deps/build/test recipes)
modified_files:
  - CMakeLists.txt              # find_package replaces FetchContent for Conan deps
  - Dockerfile                  # Add conan install layer (if Docker build exists)

# E2E validation files (meta-repo level)
e2e_files:
  - e2e/validate-conan-install.sh    # Conan export + consumer build + cmake install
  - e2e/conan-consumer/conanfile.py  # Consumer requiring all C++ packages
  - e2e/conan-consumer/CMakeLists.txt
  - e2e/conan-consumer/main.cpp
  - e2e/validate-pip-install.sh      # Python packages in clean venvs

# Conan profile (GCC 14, C++20)
conan_profile: |
  [settings]
  os=Linux
  compiler=gcc
  compiler.version=14
  compiler.libcxx=libstdc++11
  compiler.cppstd=20
  build_type=Debug  # or Release for default profile
  arch=x86_64
```

### CMake visibility rule for Conan deps in public headers

If a library's PUBLIC header (`#include <dep/header.h>`) uses a Conan dep, link that dep as `PUBLIC`
so include paths propagate to all consumers. `PRIVATE` is only correct if the dep is used exclusively
in `.cpp` sources and never appears in any installed header.

**Symptom of wrong visibility:** CMake configure succeeds (targets exist), but compilation fails with
`fatal error: 'dep/header.h' file not found` in consumer code that includes your library's headers.

```cmake
# WRONG — spdlog PRIVATE even though logger.hpp (#include <spdlog/fmt/fmt.h>) is a public header
target_link_libraries(keystone_concurrency
  PUBLIC keystone_core
  PRIVATE spdlog::spdlog)          # BAD: include dirs don't propagate

# CORRECT — both PUBLIC because public headers expose these deps
target_link_libraries(keystone_concurrency
  PUBLIC
    keystone_core
    spdlog::spdlog
    concurrentqueue::concurrentqueue)

# Audit pattern: grep public headers before choosing visibility
grep -r "#include <spdlog/"        include/   # → any hit means spdlog must be PUBLIC
grep -r "#include <concurrentqueue" include/  # → any hit means concurrentqueue must be PUBLIC
grep -r "#include <nlohmann/"      include/   # → any hit means nlohmann_json must be PUBLIC
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectAgamemnon | Hybrid Conan migration | Conan (httplib, json, gtest) + FetchContent (nats.c), 2/2 tests pass |
| ProjectNestor | Hybrid Conan migration | Same pattern, 26/26 tests pass |
| ProjectCharybdis | Conan-only (gtest) | No FetchContent deps, build succeeds |
| ProjectKeystone | Complex hybrid migration (v1.1.0) | Conan (spdlog, concurrentqueue, gtest, benchmark) + FetchContent (cista), 6 deps migrated, optional yaml-cpp for gRPC |
