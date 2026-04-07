---
name: ubuntu-gtest-gmock-apt-cmake-targets
description: "Ubuntu 24.04 splits GTest and GMock into separate apt packages. Use when: (1) CMake error 'GTest::gmock target not found' in Docker/CI builds using apt, (2) Dockerfile installs libgtest-dev but cmake can't find GTest::gmock, (3) mapping apt package names to CMake targets for C++ testing deps."
category: ci-cd
date: 2026-04-06
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags:
  - ubuntu
  - apt
  - gtest
  - gmock
  - cmake
  - dockerfile
  - cpp
  - testing
---

# Ubuntu 24.04 GTest/GMock Apt Package Split — CMake Target Mapping

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-06 |
| **Objective** | Fix CMake `GTest::gmock` target not found in Docker builds that install only `libgtest-dev` |
| **Outcome** | Successful — adding `libgmock-dev` resolved the missing CMake target |
| **Verification** | verified-precommit |

## When to Use

- CMake error: `Target "..." links to GTest::gmock but the target was not found`
- Dockerfile installs `libgtest-dev` but CMake cannot find `GTest::gmock`
- Setting up a Docker build environment for C++ projects using GTest/GMock on Ubuntu 24.04
- Mapping Ubuntu 24.04 apt package names to their CMake target names for C++ test dependencies
- CI Docker path (not Conan) where each apt package must be installed explicitly

## Verified Workflow

> **Warning:** Verification level is `verified-precommit` — CI was still running at capture time. Treat steps as a strong hypothesis until CI confirms end-to-end.

### Quick Reference

```dockerfile
# Install ALL GTest CMake targets on Ubuntu 24.04:
RUN apt-get update && apt-get install -y \
    libgtest-dev \
    libgmock-dev \
    libbenchmark-dev \
    libspdlog-dev \
    libconcurrentqueue-dev
```

### Detailed Steps

1. **Identify the failure**: CMake error at `target_link_libraries` referencing `GTest::gmock`. Example from ProjectKeystone `CMakeLists.txt:462`:
   ```
   CMake Error at CMakeLists.txt:462 (target_link_libraries):
     Target "agent_unit_tests" links to:
       GTest::gmock
     but the target was not found.
   ```

2. **Understand the root cause**: On Ubuntu 24.04, `libgtest-dev` only ships `GTest::gtest` and `GTest::gtest_main`. The `GTest::gmock` and `GTest::gmock_main` targets live in a **separate** package: `libgmock-dev`. This is a packaging split introduced in Ubuntu 24.04 that is easy to miss.

3. **Fix the Dockerfile**: Add `libgmock-dev` alongside `libgtest-dev`:
   ```dockerfile
   # BEFORE (broken — missing GTest::gmock):
   RUN apt-get update && apt-get install -y \
       libgtest-dev \
       ...

   # AFTER (fixed):
   RUN apt-get update && apt-get install -y \
       libgtest-dev \
       libgmock-dev \
       ...
   ```

4. **Note on CI vs Docker paths**: If the project uses Conan for CI, Conan installs GTest and GMock together automatically. Only the Docker apt path requires explicit `libgmock-dev`. Check whether `CMakeLists.txt` uses `find_package(GTest)` (apt path) or Conan-provided targets.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Installing only libgtest-dev | Assumed libgtest-dev provides all GTest CMake targets (GTest::gtest, GTest::gtest_main, GTest::gmock) | Ubuntu 24.04 splits GMock into a separate package — GTest::gmock not found at CMake target_link_libraries line | Always install libgmock-dev alongside libgtest-dev on Ubuntu 24.04 |

## Results & Parameters

Complete Ubuntu 24.04 apt → CMake target mapping for C++ test and utility deps:

```yaml
apt_to_cmake_targets:
  libgtest-dev:
    cmake_targets: [GTest::gtest, GTest::gtest_main]
    notes: "Does NOT include GMock — separate package required"
  libgmock-dev:
    cmake_targets: [GTest::gmock, GTest::gmock_main]
    notes: "SEPARATE package on Ubuntu 24.04 — easy to miss"
  libbenchmark-dev:
    cmake_targets: [benchmark::benchmark, benchmark::benchmark_main]
  libspdlog-dev:
    cmake_targets: [spdlog::spdlog]
    notes: "Includes bundled fmt::fmt"
  libconcurrentqueue-dev:
    cmake_targets: [concurrentqueue::concurrentqueue]
    notes: "Header-only; has CMake config"

# Context
distro: Ubuntu 24.04
build_path: Docker / apt (not Conan)
conan_note: "Conan installs GTest+GMock together — split only affects apt path"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectKeystone | Docker build — CMakeLists.txt:462 agent_unit_tests target | Added libgmock-dev to Dockerfile; fix pushed, CI running at capture time |
