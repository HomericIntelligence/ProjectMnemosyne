---
name: conan-hybrid-cpp20-turnkey-packaging
description: "Hybrid Conan 2.x + FetchContent packaging for C++20 CMake repos. Use when: (1) migrating a FetchContent-only project to Conan, (2) some deps aren't on ConanCenter so you need both, (3) integrating Conan with CMakePresets.json."
category: tooling
date: 2026-03-31
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - conan
  - cmake
  - fetchcontent
  - cpp20
  - packaging
---

# Hybrid Conan 2.x + FetchContent for C++20 CMake Projects

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-31 |
| **Objective** | Migrate C++20 CMake repos from pure FetchContent to hybrid Conan + FetchContent: Conan for well-supported packages, FetchContent for niche deps not on ConanCenter |
| **Outcome** | Successful — 3 repos (Agamemnon 2/2, Nestor 26/26, Charybdis) build and test with hybrid deps |
| **Verification** | verified-local |

## When to Use

- Migrating a C++20 CMake project from FetchContent-only to Conan for binary caching and faster rebuilds
- A dependency is not reliably on ConanCenter (e.g., nats.c) but others are (cpp-httplib, nlohmann_json, gtest)
- Integrating Conan 2.x with CMakePresets.json (v8) — getting the toolchainFile path right

## Verified Workflow

### Quick Reference

```bash
conan install . --output-folder=build/debug --profile=conan/profiles/debug --build=missing
cmake --preset debug
cmake --build --preset debug
ctest --preset debug
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

### Step 2: Update CMakeLists.txt (hybrid pattern)

Replace FetchContent for Conan-managed deps with `find_package`. Keep FetchContent for the rest.

```cmake
# Conan deps
find_package(httplib REQUIRED)
find_package(nlohmann_json REQUIRED)

# FetchContent deps (not on ConanCenter)
include(FetchContent)
FetchContent_Declare(nats_c ...)
FetchContent_MakeAvailable(nats_c)
```

Target names (`httplib::httplib`, `nlohmann_json::nlohmann_json`, `GTest::gtest_main`) are identical between Conan and FetchContent — no `target_link_libraries` changes needed for those.

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

### Step 4: Replace FetchContent(gtest) in test/CMakeLists.txt

```cmake
# BEFORE
include(FetchContent)
FetchContent_Declare(googletest ...)
FetchContent_MakeAvailable(googletest)

# AFTER
find_package(GTest REQUIRED)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `cmake_layout(self)` in conanfile.py | Used Conan's cmake_layout for automatic output paths | Creates nested `build/Debug/generators/` that doesn't match CMakePresets `build/${presetName}` convention | Remove `cmake_layout()` — use explicit `--output-folder`. Generators land directly in the specified directory. |
| Stale CMakeCache after migration | Configured CMake with FetchContent, then added Conan toolchain | Old CMakeCache.txt ignores `CMAKE_TOOLCHAIN_FILE` — CMake warns "Manually-specified variables were not used" | Always delete `build/` before first Conan build. Stale FetchContent cache silently ignores the Conan toolchain. |
| Full Conan replacement for nats.c | Tried `cnats` Conan package for nats.c | cnats availability/version uncertain on ConanCenter — risk of mismatch | Hybrid approach: Conan for well-supported packages, FetchContent for niche ones |

## Results & Parameters

```yaml
# Conan target name mapping (identical to FetchContent names)
httplib: httplib::httplib
nlohmann_json: nlohmann_json::nlohmann_json
gtest: GTest::gtest_main
# FetchContent targets unchanged
nats_static: nats_static

# File changes per repo
new_files:
  - conanfile.py
  - conan/profiles/default
  - conan/profiles/debug
modified_files:
  - CMakeLists.txt         # find_package replaces FetchContent for Conan deps
  - test/CMakeLists.txt    # find_package(GTest) replaces FetchContent(googletest)
  - CMakePresets.json      # Add toolchainFile to base preset
  - pixi.toml              # Add conan dependency
  - justfile               # Add deps recipe
  - Dockerfile             # Add conan install layer
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectAgamemnon | Hybrid Conan migration | Conan (httplib, json, gtest) + FetchContent (nats.c), 2/2 tests pass |
| ProjectNestor | Hybrid Conan migration | Same pattern, 26/26 tests pass |
| ProjectCharybdis | Conan-only (gtest) | No FetchContent deps, build succeeds |
