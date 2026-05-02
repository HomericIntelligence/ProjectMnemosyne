---
name: cmake-cxx-warnings-fetchcontent-c-lib
description: "Scope CMake warning flags to C++ only when using FetchContent C libraries. Use when: (1) a C library pulled via FetchContent fails to compile with -Werror,-Wunused-parameter or -Wunused-function, (2) you see compiler errors in third-party C files you did not author, (3) adding any C library (nats.c, libuv, etc.) to a C++20 project with global -Wall -Wextra -Wpedantic -Werror flags."
category: ci-cd
date: 2026-04-23
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - cmake
  - compiler-warnings
  - fetchcontent
  - c-library
  - generator-expressions
  - nats
  - werror
  - cpp20
---

# CMake C++ Warning Flags Breaking FetchContent C Libraries

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-23 |
| **Objective** | Prevent global `-Wall -Wextra -Wpedantic -Werror` from breaking third-party C libraries pulled via FetchContent |
| **Outcome** | Successful — CI builds (asan/lsan/ubsan) passed after scoping flags to C++ only |
| **Verification** | verified-ci — merged as PR #379 in ProjectKeystone |

## When to Use

- Adding any C library via CMake `FetchContent_Declare` / `FetchContent_MakeAvailable` to a C++20 project
- Seeing compilation errors in third-party C files (files you did not author) such as:
  - `error: unused parameter 'scPtr' [-Werror,-Wunused-parameter]`
  - `error: unused function 'foo' [-Werror,-Wunused-function]`
- You have `add_compile_options(-Wall -Wextra -Wpedantic -Werror)` applied globally (not per-target)
- After adding nats.c, libuv, sqlite, or any other C library via FetchContent and CI starts failing on the C library's own source files

## Verified Workflow

### Quick Reference

```cmake
# BEFORE (broken — applies to ALL languages including C):
add_compile_options(-Wall -Wextra -Wpedantic -Werror)

# AFTER (correct — restricts to C++ translation units only):
add_compile_options(
  $<$<COMPILE_LANGUAGE:CXX>:-Wall>
  $<$<COMPILE_LANGUAGE:CXX>:-Wextra>
  $<$<COMPILE_LANGUAGE:CXX>:-Wpedantic>
  $<$<COMPILE_LANGUAGE:CXX>:-Werror>)

# Also apply generator expressions to any GCC-specific C++ suppressions:
add_compile_options($<$<COMPILE_LANGUAGE:CXX>:-Wno-dangling-reference>)
```

### Detailed Steps

1. Open the project's `CMakeLists.txt` (or the file where `add_compile_options` is called globally)
2. Find every `add_compile_options(...)` call that adds warning/error flags without a language guard
3. Wrap each flag with `$<$<COMPILE_LANGUAGE:CXX>:flag>` generator expression
4. Verify nats.c (or your C library) now compiles without errors:
   ```bash
   cmake --preset asan && cmake --build --preset asan
   ```
5. Confirm your own C++ code still gets all the warnings you want:
   ```bash
   # Introduce a deliberate unused parameter in a .cpp file — should still error
   ```
6. Run full CI sanitizer matrix:
   ```bash
   cmake --preset asan && cmake --build --preset asan && ctest --preset asan
   cmake --preset tsan && cmake --build --preset tsan && ctest --preset tsan
   cmake --preset ubsan && cmake --build --preset ubsan && ctest --preset ubsan
   ```

### Root Cause

`add_compile_options(...)` without a `COMPILE_LANGUAGE` generator expression applies to **all** languages the project compiles, including C. When `FetchContent_MakeAvailable` pulls in a C library, that library's `.c` files are compiled as part of the same CMake project and inherit the project's global compile options — including `-Werror`. Third-party C code authored without strict warning discipline will then fail to compile.

The generator expression `$<$<COMPILE_LANGUAGE:CXX>:flag>` is evaluated per-translation-unit at build time and inserts the flag only when the compiler is invoked for a C++ source file.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Leave flags as-is | Keep `-Wall -Wextra -Wpedantic -Werror` globally | nats.c `asynccb.c:32` failed: `error: unused parameter 'scPtr' [-Werror,-Wunused-parameter]` | Global flags apply to all languages — never use without language guard when mixing C and C++ |
| Add `-Wno-unused-parameter` globally | Suppress unused-parameter for all targets | Would silence useful warnings in the project's own C++ code, defeating the purpose of `-Wall` | Global suppression is too broad; scoping the error flags is the correct fix |
| Use `target_compile_options` on FetchContent target | Try to remove flags from the nats.c target after `FetchContent_MakeAvailable` | FetchContent targets may not be easily addressable by name before MakeAvailable; fragile and order-dependent | Fix the source (global flags scope) rather than patching the downstream target |

## Results & Parameters

```cmake
# Final verified configuration in CMakeLists.txt:
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

```yaml
# Context where this was verified:
project: ProjectKeystone
pr: "#379"
c_library: nats.c v3.12.0
fetch_method: FetchContent_Declare / FetchContent_MakeAvailable
failing_file: nats.c/src/asynccb.c:32
failing_error: "error: unused parameter 'scPtr' [-Werror,-Wunused-parameter]"
ci_presets_tested: [asan, lsan, ubsan]
ci_result: all passing after fix
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectKeystone | CI builds broken by nats.c v3.12.0 FetchContent integration | PR #379, asan/lsan/ubsan all passed after scoping warning flags to CXX |

## See Also

- [`natsc-fetchcontent-cpp20-integration`](./natsc-fetchcontent-cpp20-integration.md) — Full nats.c FetchContent setup for C++20 projects (API usage, JetStream, include paths)
