---
name: conan-cmake-toolchain-coverage-scripts
description: "Coverage scripts in Conan-managed C++ projects must explicitly pass the Conan toolchain file to cmake or find_package() calls will fail. Use when: (1) Code Coverage CI job fails with cmake find_package errors while other CI jobs (tests, benchmarks) pass, (2) generate_coverage.sh or similar scripts invoke cmake without -DCMAKE_TOOLCHAIN_FILE, (3) GTest/other Conan-managed deps are missing only in coverage builds."
category: ci-cd
date: 2026-04-23
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - conan
  - cmake
  - coverage
  - toolchain
  - gtest
  - ci-cd
  - cpp20
---

# Conan CMake Toolchain Required in Coverage Scripts

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-23 |
| **Objective** | Fix `Code Coverage` CI job failing with `Could NOT find GTest` when Conan 2 manages dependencies |
| **Outcome** | Success — Coverage CI passed after adding `-DCMAKE_TOOLCHAIN_FILE` to coverage script cmake invocation |
| **Verification** | verified-ci |
| **History** | N/A (initial version) |

## When to Use

- `Code Coverage` CI job fails with cmake `find_package` errors (e.g. `Could NOT find GTest (missing: GTEST_LIBRARY GTEST_INCLUDE_DIR GTEST_MAIN_LIBRARY)`)
- Other CI jobs (tests, benchmarks, sanitizers) pass — meaning deps ARE available via Conan toolchain
- Project uses Conan 2 with `conan_toolchain.cmake` for dependency management
- A shell script (`generate_coverage.sh`, `run_coverage.sh`, etc.) invokes cmake directly without inheriting the Makefile/preset build context
- CI coverage job does two phases: (1) build+test via Makefile, (2) invoke a coverage shell script

## Verified Workflow

### Quick Reference

```bash
# Locate the Conan toolchain (standard Conan 2 output location)
CONAN_TOOLCHAIN="$PROJECT_ROOT/build/conan-deps/conan_toolchain.cmake"

# WRONG — missing toolchain:
cmake -DENABLE_COVERAGE=ON -DCMAKE_BUILD_TYPE=Debug -G Ninja "$PROJECT_ROOT"

# CORRECT — pass toolchain conditionally:
CMAKE_ARGS=(-DENABLE_COVERAGE=ON -DCMAKE_BUILD_TYPE=Debug -G Ninja)
if [[ -f "$CONAN_TOOLCHAIN" ]]; then
    CMAKE_ARGS+=(-DCMAKE_TOOLCHAIN_FILE="$CONAN_TOOLCHAIN")
fi
cmake "${CMAKE_ARGS[@]}" "$PROJECT_ROOT"
```

### Detailed Steps

1. Identify the failing CI job — look for `find_package` errors mentioning Conan-managed deps (GTest, Catch2, etc.)

2. Locate the coverage script invoked by CI (e.g. `scripts/generate_coverage.sh`, `tools/coverage.sh`)

3. Find the cmake invocation in that script:
   ```bash
   grep -n "cmake " scripts/generate_coverage.sh
   ```

4. Check if `-DCMAKE_TOOLCHAIN_FILE` is present. If not, this is the bug.

5. Find the standard Conan toolchain path for the project:
   ```bash
   find build/ -name "conan_toolchain.cmake" 2>/dev/null
   # Typically: build/conan-deps/conan_toolchain.cmake
   ```

6. Patch the script to pass the toolchain conditionally (so it also works in environments without Conan):
   ```bash
   CONAN_TOOLCHAIN="$PROJECT_ROOT/build/conan-deps/conan_toolchain.cmake"
   CMAKE_ARGS=(-DENABLE_COVERAGE=ON -DCMAKE_BUILD_TYPE=Debug -G Ninja)
   if [[ -f "$CONAN_TOOLCHAIN" ]]; then
       CMAKE_ARGS+=(-DCMAKE_TOOLCHAIN_FILE="$CONAN_TOOLCHAIN")
   fi
   cmake "${CMAKE_ARGS[@]}" "$PROJECT_ROOT"
   ```

7. Also check: does the script use `..` as the cmake source directory after `cd "$BUILD_DIR"`?
   - `..` resolves to the build parent, which may not be `$PROJECT_ROOT` in all CI environments
   - Use `"$PROJECT_ROOT"` as an explicit absolute path instead

8. Commit the fix and push. The CI coverage job should find all Conan-managed dependencies.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Bare cmake invocation | `cmake -DENABLE_COVERAGE=ON -DCMAKE_BUILD_TYPE=Debug -G Ninja "$PROJECT_ROOT"` | Conan toolchain not passed; `find_package(GTest)` cannot locate Conan-installed GTest | Shell scripts don't inherit cmake preset or Makefile context — toolchain must be explicit |
| Relative source path | `cd "$BUILD_DIR" && cmake .. -DENABLE_COVERAGE=ON ...` | `..` resolves to build parent which may differ from `$PROJECT_ROOT` in CI | Always use `"$PROJECT_ROOT"` as an explicit absolute path for the cmake source directory |
| Assuming Makefile context propagates | Expected coverage script to "just work" because the Makefile build passed | Each cmake invocation is independent — no shared context between Makefile and scripts | Every cmake call in a Conan project needs `-DCMAKE_TOOLCHAIN_FILE` if it runs `find_package` |

## Results & Parameters

```bash
# Standard Conan 2 toolchain location
CONAN_TOOLCHAIN="$PROJECT_ROOT/build/conan-deps/conan_toolchain.cmake"

# Verified fix pattern for generate_coverage.sh
CMAKE_ARGS=(-DENABLE_COVERAGE=ON -DCMAKE_BUILD_TYPE=Debug -G Ninja)
if [[ -f "$CONAN_TOOLCHAIN" ]]; then
    CMAKE_ARGS+=(-DCMAKE_TOOLCHAIN_FILE="$CONAN_TOOLCHAIN")
fi
cmake "${CMAKE_ARGS[@]}" "$PROJECT_ROOT"
```

**Root cause summary**: CI coverage jobs often have two phases:
1. Makefile/CMakePreset build+test — uses Conan toolchain automatically
2. Coverage shell script invokes cmake directly — does NOT inherit toolchain context

Phase 1 passes because CMakePresets or the Makefile include `-DCMAKE_TOOLCHAIN_FILE`.
Phase 2 fails silently because the shell script omits it, and `find_package(GTest)` cannot find Conan-installed packages.

**Diagnostic signal**: If tests pass in all other CI jobs but `Code Coverage` fails with `find_package` errors, always audit the coverage script for missing `-DCMAKE_TOOLCHAIN_FILE`.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectKeystone | PR #340 Code Coverage CI job — verified-ci 2026-04-23 | `Code Coverage: FAIL` → fixed by adding `-DCMAKE_TOOLCHAIN_FILE` to `generate_coverage.sh`; Benchmarks/Tests 4/5 passed |
