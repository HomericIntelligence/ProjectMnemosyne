---
name: conan-hybrid-cpp20-turnkey-packaging
description: "Hybrid Conan 2.x + FetchContent packaging for C++20 repos with pixi. Use when: (1) adding Conan to a C++20 project that already uses FetchContent, (2) some deps aren't on ConanCenter (e.g., nats.c), (3) making a C++ repo turnkey installable via pixi + just, (4) OpenSSL linker errors with pixi conda-forge sysroot."
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
  - pixi
  - packaging
  - turnkey
  - openssl
---

# Hybrid Conan 2.x + FetchContent for C++20 Turnkey Packaging

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-31 |
| **Objective** | Make C++20 repos turnkey: `pixi install && just build` on a fresh machine. Migrate well-supported deps to Conan, keep niche deps on FetchContent. |
| **Outcome** | Successful — ProjectAgamemnon (2/2 tests), ProjectNestor (26/26 tests), ProjectCharybdis all build with hybrid Conan + FetchContent |
| **Verification** | verified-local |

## When to Use

- Adding Conan 2.x to a C++20 project that already uses CMake FetchContent for all deps
- Some dependencies are not reliably on ConanCenter (e.g., nats.c / cnats) while others are (cpp-httplib, nlohmann_json, gtest)
- Making a C++ repo "turnkey" installable: `pixi install && just deps && just build`
- Encountering GLIBC_PRIVATE linker errors when mixing system OpenSSL with pixi conda-forge compiler
- Setting up Conan profiles for GCC 14 + C++20 in a pixi-managed environment
- Updating Dockerfiles for multi-stage builds with Conan dependency layer caching

## Verified Workflow

### Quick Reference

```bash
# Per-repo standalone build (after pixi is installed)
cd ProjectFoo
pixi install                    # cmake, ninja, gcc, conan, openssl
just deps                       # conan install --build=missing
just build                      # cmake --preset debug && build
just test                       # ctest
```

### Step 1: Create conanfile.py (Conan deps only — not nats.c)

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

**CRITICAL: Do NOT use `cmake_layout(self)`** — it creates nested `build/Debug/generators/` paths that conflict with CMakePresets.json `build/${presetName}` convention. Without `cmake_layout`, `--output-folder` puts generators directly in the specified directory.

### Step 2: Create Conan profiles

```
# conan/profiles/debug
[settings]
os=Linux
compiler=gcc
compiler.version=14    # Match pixi conda-forge GCC version!
compiler.libcxx=libstdc++11
compiler.cppstd=20
build_type=Debug
arch=x86_64
```

**CRITICAL: Check your pixi GCC version** with `pixi run g++ --version`. conda-forge currently ships GCC 14, not 13.

### Step 3: Update CMakeLists.txt (hybrid pattern)

```cmake
# Conan deps (run `just deps` first)
find_package(httplib REQUIRED)
find_package(nlohmann_json REQUIRED)
find_package(OpenSSL REQUIRED)  # Needed for nats.c static linking

# FetchContent deps (not on ConanCenter)
include(FetchContent)
FetchContent_Declare(nats_c
  GIT_REPOSITORY https://github.com/nats-io/nats.c.git
  GIT_TAG v3.9.1
  GIT_SHALLOW TRUE)
set(NATS_BUILD_STREAMING OFF CACHE BOOL "" FORCE)
set(NATS_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(BUILD_TESTING_SAVED "${BUILD_TESTING}")
set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(nats_c)
set(BUILD_TESTING "${BUILD_TESTING_SAVED}" CACHE BOOL "" FORCE)

# Link — nats_static needs OpenSSL explicitly
target_link_libraries(my_server PRIVATE
  httplib::httplib
  nlohmann_json::nlohmann_json
  nats_static
  OpenSSL::SSL
  OpenSSL::Crypto)
```

### Step 4: Update CMakePresets.json

Add `toolchainFile` to base preset:
```json
{
  "name": "base",
  "hidden": true,
  "generator": "Ninja",
  "binaryDir": "${sourceDir}/build/${presetName}",
  "toolchainFile": "${sourceDir}/build/${presetName}/conan_toolchain.cmake",
  "cacheVariables": { "CMAKE_EXPORT_COMPILE_COMMANDS": "ON" }
}
```

### Step 5: Update pixi.toml

```toml
[dependencies]
cmake = ">=3.20"
ninja = ">=1.11"
cxx-compiler = ">=1.7"
conan = ">=2.0"
openssl = ">=3"          # CRITICAL: must match conda-forge sysroot
clang-tools = ">=17"
gcovr = ">=7"
pre-commit = ">=3"

[tasks]
deps = "conan install . --output-folder=build/debug --profile=conan/profiles/debug --build=missing"
build = { cmd = "cmake --preset debug && cmake --build --preset debug", depends-on = ["deps"] }
test = "ctest --preset debug --output-on-failure"
```

### Step 6: Update justfile

```just
deps:
  conan install . --output-folder=build/debug --profile=conan/profiles/debug --build=missing

build: deps
  cmake --preset debug && cmake --build --preset debug

test:
  ctest --preset debug --output-on-failure
```

### Step 7: Update Dockerfile (multi-stage with Conan)

```dockerfile
FROM ubuntu:24.04 AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake ninja-build g++ git ca-certificates libssl-dev python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install --break-system-packages conan

WORKDIR /src
COPY conanfile.py conan/ ./
RUN conan install . --output-folder=build --profile=conan/profiles/default --build=missing

COPY CMakeLists.txt CMakePresets.json cmake/ include/ src/ test/ ./
RUN cmake -B build -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE=build/conan_toolchain.cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DProjectFoo_BUILD_TESTING=OFF \
    && cmake --build build --target ProjectFoo_server

FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends libssl3 wget && rm -rf /var/lib/apt/lists/*
COPY --from=builder /src/build/ProjectFoo_server /usr/local/bin/
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `cmake_layout(self)` in conanfile.py | Used Conan's cmake_layout for automatic paths | Creates nested `build/Debug/generators/` path that doesn't match CMakePresets `build/${presetName}` convention | Remove `cmake_layout()` and use explicit `--output-folder` with Conan. Generators go directly into the output folder. |
| Conan profile `compiler.version=13` | Assumed GCC 13 | pixi conda-forge ships GCC 14.3.0 — Conan profile mismatch causes package hash errors | Always check `pixi run g++ --version` and match the Conan profile |
| System OpenSSL with pixi linker | `find_package(OpenSSL)` found `/usr/lib/x86_64-linux-gnu/libssl.so` | pixi's conda-forge linker uses a different sysroot — GLIBC_PRIVATE symbols undefined (`__libc_siglongjmp@GLIBC_PRIVATE`, `_dl_sym@GLIBC_PRIVATE`) | Add `openssl = ">=3"` to pixi.toml dependencies so OpenSSL comes from conda-forge, compatible with the conda-forge sysroot and linker |
| Stale CMakeCache.txt after switching to Conan | Configured CMake with FetchContent, then added Conan toolchain | Old CMakeCache.txt ignores `CMAKE_TOOLCHAIN_FILE` — CMake warns "Manually-specified variables were not used" | Always delete `build/debug/` before first Conan build. Stale cache from FetchContent era will silently ignore the Conan toolchain. |
| Python stub healthchecks in compose | Used `python3 -c "import urllib.request..."` for healthchecks | C++ runtime images (ubuntu:24.04 slim) don't have Python installed | Use `wget -qO-` for healthchecks in compose files when containers run compiled C++ binaries |
| cnats on ConanCenter | Tried to replace all FetchContent with Conan including nats.c | cnats package availability uncertain on ConanCenter — risk of version mismatch | Hybrid approach: Conan for well-supported packages (cpp-httplib, nlohmann_json, gtest), FetchContent for niche ones (nats.c) |

## Results & Parameters

```yaml
# Verified dependency mapping
conan_deps:
  - cpp-httplib/0.18.3   # ConanCenter: available, header-only
  - nlohmann_json/3.11.3 # ConanCenter: available, header-only
  - gtest/1.14.0         # ConanCenter: available, built from source for Debug

fetchcontent_deps:
  - nats.c v3.9.1        # Not reliably on ConanCenter, keep FetchContent

pixi_tool_deps:
  - cmake >= 3.20
  - ninja >= 1.11
  - cxx-compiler >= 1.7   # GCC 14 from conda-forge
  - conan >= 2.0
  - openssl >= 3           # MUST be from conda-forge for sysroot compat

# Build times (local, clean build)
agamemnon_build: ~120s (96 targets — includes nats.c FetchContent)
nestor_build: ~100s (100 targets)
charybdis_build: ~5s (4 targets — no nats.c)

# Test results
agamemnon_tests: 2/2 pass
nestor_tests: 26/26 pass
charybdis_tests: builds (pre-existing test harness issue)

# Conan target name mapping (Conan → CMake target)
httplib: httplib::httplib  # Same as FetchContent — no change needed
nlohmann_json: nlohmann_json::nlohmann_json  # Same as FetchContent
gtest: GTest::gtest_main  # Same as FetchContent
nats_static: nats_static  # FetchContent — unchanged

# Turnkey flow (fresh Ubuntu 24.04)
install_steps:
  1: "curl -fsSL https://pixi.sh/install.sh | bash"
  2: "git clone --recursive https://github.com/HomericIntelligence/Odysseus.git && cd Odysseus"
  3: "pixi install && just bootstrap"
  4: "just build"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectAgamemnon | Hybrid Conan packaging | C++20 REST server: Conan (httplib, json, gtest) + FetchContent (nats.c) + OpenSSL |
| ProjectNestor | Hybrid Conan packaging | C++20 research server: same hybrid pattern, 26 tests passing |
| ProjectCharybdis | Conan-only packaging | C++20 test library: only gtest via Conan, no FetchContent deps |
| Odysseus (root) | Cross-repo orchestration | justfile delegates `pixi run conan install` per submodule |
