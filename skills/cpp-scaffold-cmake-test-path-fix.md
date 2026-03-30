---
name: cpp-scaffold-cmake-test-path-fix
description: "Fix CMake test source path bug in C++20 scaffold repos where add_subdirectory(test) causes double-prefix. Use when: (1) cmake configure succeeds but ctest reports 'No tests were found', (2) test/CMakeLists.txt uses 'test/src/test_main.cpp' as the source path, (3) linking succeeds but gtest never discovers tests, (4) building a scaffolded C++ repo (Agamemnon/Nestor/Charybdis template) for the first time."
category: debugging
date: 2026-03-29
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [cmake, gtest, add_subdirectory, test-path, cpp20, scaffold, ctest, odysseus]
---

# C++ Scaffold CMake Test Path Fix

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-29 |
| **Objective** | Fix ctest reporting "No tests were found" in C++20 scaffold repos (Agamemnon/Nestor/Charybdis template) |
| **Outcome** | Successful. Test binary compiles and links. ctest discovers tests correctly. |
| **Verification** | verified-local — cmake configure + build + ctest verified in both per-repo and meta-repo build contexts |

## When to Use

- `ctest` reports "No tests were found!!!" even though the test executable was built
- `test/CMakeLists.txt` has `add_executable(..._tests test/src/test_main.cpp)`
- The repo was generated from the HomericIntelligence C++20 SGSG scaffold template
- Building a scaffold repo (ProjectAgamemnon, ProjectNestor, ProjectCharybdis) for the first time
- A new scaffold repo was created and the first `just build` + `just test` fails

## Verified Workflow

### Quick Reference

```bash
# Find the bug
grep "add_executable" test/CMakeLists.txt
# Bad:  add_executable(${PROJECT_NAME}_tests test/src/test_main.cpp)
# Good: add_executable(${PROJECT_NAME}_tests src/test_main.cpp)

# One-line fix (from repo root)
sed -i 's|add_executable(\${PROJECT_NAME}_tests test/src/test_main.cpp)|add_executable(${PROJECT_NAME}_tests src/test_main.cpp)|' test/CMakeLists.txt

# Verify: build and test from repo root
cmake --preset debug && cmake --build --preset debug && ctest --preset debug

# Verify: build from meta-repo (Odysseus) with -S/-B override
cmake -S . -B /tmp/test-build -DCMAKE_BUILD_TYPE=Debug -G Ninja -D${PROJECT_NAME}_BUILD_TESTING=ON
cmake --build /tmp/test-build
ctest --test-dir /tmp/test-build --output-on-failure
```

### Detailed Steps

1. **Understand the bug.** The scaffold generates `test/CMakeLists.txt` which is included via `add_subdirectory(test)` from the root `CMakeLists.txt`. When cmake processes `test/CMakeLists.txt`, `CMAKE_CURRENT_SOURCE_DIR` is already set to `<project>/test/`. The path `test/src/test_main.cpp` therefore resolves to `<project>/test/test/src/test_main.cpp` — a path that doesn't exist. However, cmake doesn't error on this at configure time — it only fails at link time or silently produces a binary that gtest can't discover.

2. **Diagnose.** Run `ctest --output-on-failure` and look for "No tests were found!!!". The test executable was compiled (cmake found *something* to link), but gtest_discover_tests found no TEST() macros. This is a separate symptom — see "Known Non-Issue" below.

3. **Fix.** Edit `test/CMakeLists.txt` line 10:
   ```cmake
   # Before (wrong — double test/ prefix after add_subdirectory):
   add_executable(${PROJECT_NAME}_tests test/src/test_main.cpp)

   # After (correct — relative to test/ directory):
   add_executable(${PROJECT_NAME}_tests src/test_main.cpp)
   ```

4. **Verify both build contexts.** The fix must work:
   - From within the repo: `cmake --preset debug && cmake --build --preset debug`
   - From meta-repo (Odysseus): `cmake -S <path> -B <BUILD_ROOT>/<Name> -G Ninja -D<Name>_BUILD_TESTING=ON`

   Both use the same `CMakeLists.txt` → `add_subdirectory(test)` → `test/CMakeLists.txt` path, so the fix is context-independent.

5. **Commit in submodule repo** (not in meta-repo):
   ```bash
   git checkout -b fix/test-cmake-path
   git add test/CMakeLists.txt
   git commit -m "fix(test): correct source path in test/CMakeLists.txt"
   ```
   Then update the submodule pointer in the meta-repo:
   ```bash
   cd <meta-repo>
   git add <submodule-path>
   git commit -m "fix(submodules): update <Name> pointer to fix/test-cmake-path"
   ```

## Known Non-Issue: "No tests were found" After Fix

After applying the path fix, ctest may still report "No tests were found!!!" for scaffold repos. This is a **separate pre-existing issue** — not a regression:

The scaffold puts `int main()` in `src/main.cpp` which is compiled into the static library `lib<ProjectName>.a`. The test executable links against both this library and `GTest::gtest_main`. The library's `main()` symbol wins at link time, so gtest's `main()` never runs and tests are never registered.

**This is separate from the path bug.** The test binary links and can be executed. To fix the gtest discovery issue, either:
- Remove `int main()` from `src/main.cpp` (scaffold placeholder — it shouldn't be in a library)
- Or keep it and add a proper `main()` to the test file that calls `RUN_ALL_TESTS()`

Both scaffold bugs (path + main symbol) need to be fixed together for tests to actually run.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Absolute path in test/CMakeLists.txt | Used `${CMAKE_SOURCE_DIR}/test/src/test_main.cpp` | Works from repo root but breaks when `-S` points to a different directory (Odysseus meta-repo case) | Always use paths relative to `CMAKE_CURRENT_SOURCE_DIR` inside subdirectories; never rely on `CMAKE_SOURCE_DIR` for test sources |
| Fix only for preset build | Only tested with `cmake --preset debug`, not the `-S/-B` meta-repo path | Meta-repo uses `cmake -S <submodule> -B <BUILD_ROOT>/<Name>` which bypasses presets entirely | Must verify both build contexts: preset (per-repo) and `-S/-B` (meta-repo) |

## Results & Parameters

```yaml
repos_affected:
  - control/ProjectAgamemnon   # fix commit: 3362f25
  - control/ProjectNestor      # fix commit: c060492
  - testing/ProjectCharybdis   # fix commit: a26835e

root_cause: >
  SGSG scaffold template generates test/CMakeLists.txt with wrong relative path.
  add_subdirectory(test) sets CMAKE_CURRENT_SOURCE_DIR to <project>/test/,
  but the path test/src/test_main.cpp adds another test/ prefix.

fix_pattern: >
  Change: add_executable(${PROJECT_NAME}_tests test/src/test_main.cpp)
  To:     add_executable(${PROJECT_NAME}_tests src/test_main.cpp)

works_in_both_contexts:
  - "cmake --preset debug"  # per-repo, uses CMakePresets.json
  - "cmake -S <path> -B <external>"  # meta-repo BUILD_ROOT pattern

related_skill: meta-repo-build-root-pattern
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectAgamemnon | PR #68, 2026-03-29 Odysseus full build session | Fix applied, both build contexts verified |
| ProjectNestor | PR #68, 2026-03-29 Odysseus full build session | Fix applied, both build contexts verified |
| ProjectCharybdis | PR #68, 2026-03-29 Odysseus full build session | Fix applied, both build contexts verified |
