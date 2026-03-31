---
name: cmake-library-main-gtest-conflict
description: "Fix ctest 'No tests were found' when library target contains main() that conflicts with GTest::gtest_main. Use when: (1) ctest reports zero tests despite test binary being built, (2) test binary runs but prints version instead of running tests, (3) CI coverage step fails with 'No tests were found'."
category: ci-cd
date: 2026-03-30
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - cmake
  - gtest
  - ctest
  - coverage
  - main-conflict
  - cpp20
---

# CMake Library main() Conflicts with GTest

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-30 |
| **Objective** | Fix `ctest` reporting zero tests when a C++20 library target includes `main()` |
| **Outcome** | Successful — tests discovered and pass after extracting `main()` from library |
| **Verification** | verified-local |

## When to Use

- `ctest --preset coverage` (or any preset) reports `No tests were found!!!`
- Test binary is built by CMake but running it prints application output (e.g., version string) instead of GTest output
- CI coverage workflow fails because ctest finds no tests to run
- Library target (`add_library`) contains a source file with a `main()` function
- Test executable links against both the library and `GTest::gtest_main`

## Verified Workflow

### Quick Reference

```bash
# Diagnosis: run test binary directly
./build/coverage/test/ProjectFoo_tests
# If it prints "ProjectFoo v0.1.0" instead of GTest output → main() conflict

# Fix: check what's in the library sources
cat cmake/SourcesAndHeaders.cmake
# If it includes src/main.cpp → that's the problem

# Fix: replace main.cpp with a stub that has no main()
```

### Detailed Steps

1. **Identify the conflict**: The library target (`add_library(ProjectFoo ...)`) includes `src/main.cpp` which has a `main()` function. The test target links `ProjectFoo::ProjectFoo` + `GTest::gtest_main`. Both provide `main()` — the library's wins (linker picks the first one).

2. **Remove main.cpp from library sources** in `cmake/SourcesAndHeaders.cmake`:
   ```cmake
   # BEFORE (broken):
   set(sources src/main.cpp)

   # AFTER (fixed):
   set(sources src/version_info.cpp)
   ```

3. **Create a stub source** (`src/version_info.cpp`) that provides library symbols without `main()`:
   ```cpp
   #include "projectfoo/version.hpp"
   namespace projectfoo {
   const char* get_version() { return kVersion.data(); }
   const char* get_project_name() { return kProjectName.data(); }
   }
   ```

4. **Keep main.cpp only in the server executable target** (in `CMakeLists.txt`):
   ```cmake
   add_executable(ProjectFoo_server
     src/server_main.cpp
     src/routes.cpp
     # main.cpp is NOT here — server_main.cpp has its own main()
   )
   ```

5. **Verify**: `ctest --preset coverage` now discovers and runs tests.

### Also Fix: Missing Coverage Test Preset

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

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Keep main.cpp in library | Library had `add_library(Foo src/main.cpp)` with test linking `Foo::Foo` + `GTest::gtest_main` | Two `main()` symbols — linker picks library's `main()`, GTest never runs | Library targets must NEVER contain `main()` |
| Make library INTERFACE | Changed `add_library(Foo ...)` to `add_library(Foo INTERFACE)` | CMake errors — INTERFACE libraries can't have source files, compile features need different syntax | Use a stub source file instead of INTERFACE |
| Set sources to empty | `set(sources "")` in SourcesAndHeaders.cmake | `add_library` with no sources fails in CMake | Must have at least one source file |
| Run clang-format only | Thought the CI failure was just formatting | ctest failure is separate from clang-format — both need fixing | Always check ALL CI failures, not just the first one |

## Results & Parameters

```yaml
# Symptom
ci_error: "No tests were found!!!"
ci_job: Coverage
ci_step: "ctest --preset coverage"
test_binary_output: "ProjectFoo v0.1.0"  # prints version instead of running GTest

# Root cause
library_sources: "src/main.cpp"  # has main() function
test_links: "ProjectFoo::ProjectFoo + GTest::gtest_main"
conflict: "two main() symbols — library's main() wins"

# Fix
new_library_source: "src/version_info.cpp"  # no main(), just version symbols
main_cpp_location: "server executable target only"

# Verification
ctest_output: |
  Test project build/coverage
  1/2 Test #1: VersionTest.ProjectNameIsCorrect ... Passed
  2/2 Test #2: VersionTest.VersionIsSet ........... Passed
  100% tests passed, 0 tests failed out of 2
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectAgamemnon | CI coverage fix | Library had main.cpp → replaced with version_info.cpp |
| ProjectNestor | CI coverage fix | Same pattern applied |
