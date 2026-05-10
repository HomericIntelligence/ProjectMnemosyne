---
name: cpp-prometheus-conan-pull-target-missing-with-pull-false
description: "Fix CMake error 'target prometheus-cpp::pull was not found' when Conan sets with_pull=False. Use when: (1) CMake configure fails with missing prometheus-cpp::pull or ::core target, (2) setting up Prometheus metrics in a C++ project with Conan, (3) deciding which prometheus-cpp CMake target to link based on conanfile options."
category: ci-cd
date: 2026-05-10
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [cpp, cmake, conan, prometheus, metrics]
---

# cpp-prometheus-conan-pull-target-missing-with-pull-false

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-10 |
| **Objective** | Add Prometheus metrics to a C++ project using Conan without the embedded HTTP pull server |
| **Outcome** | Successful — PR #292 (ProjectAgamemnon Prometheus metrics) went green after fix |
| **Verification** | verified-ci |

## When to Use

- CMake configure error: `target prometheus-cpp::pull was not found`
- CMake configure error: `target prometheus-cpp::core was not found`
- Setting up Prometheus metrics in a C++ project that uses Conan
- Conan + CMake + `prometheus-cpp` library integration
- Choosing between `prometheus-cpp::core`, `prometheus-cpp::pull`, or `prometheus-cpp::push` targets
- Working with Conan's `with_pull` / `with_push` / `with_compression` options

## Verified Workflow

### Quick Reference

```cmake
# CMakeLists.txt — link the right component

# For emitting text/openmetrics output only (most common case, GET /metrics):
target_link_libraries(${PROJECT_NAME} PUBLIC prometheus-cpp::core)

# If you need the embedded HTTP pull server (pull model), ensure conanfile.py has:
# self.options["prometheus-cpp"].with_pull = True
# Then link:
# target_link_libraries(${PROJECT_NAME} PRIVATE prometheus-cpp::pull)
```

```python
# conanfile.py — ensure options match what CMakeLists.txt links
def configure(self):
    self.options["prometheus-cpp"].with_pull = False   # no embedded HTTP server
    self.options["prometheus-cpp"].with_push = False   # no pushgateway client
    self.options["prometheus-cpp"].with_compression = False
```

### Detailed Steps

1. Identify the error: CMake configure fails with `target prometheus-cpp::pull was not found`.
2. Check `conanfile.py` `configure()` method — note whether `with_pull` is `True` or `False`.
3. Check `CMakeLists.txt` — find all `target_link_libraries` calls that reference `prometheus-cpp::*`.
4. Apply the fix: if `with_pull=False`, replace every `prometheus-cpp::pull` reference with `prometheus-cpp::core`.
5. Use `PUBLIC` (not `PRIVATE`) on the library target so that consumers (test fixtures, other libs) that transitively include the metrics headers automatically get the dependency propagated.
6. Check every CMake target that includes the metrics header (directly or transitively). Each one must eventually link `prometheus-cpp::core` — either directly or through a `PUBLIC` transitive dependency.
7. Run `conan install` + `cmake ..` to confirm no more missing-target errors.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Linked `prometheus-cpp::pull` in CMakeLists.txt while conanfile had `with_pull=False` | Conan only generates a CMake target for components whose matching `with_*` option is enabled. With `with_pull=False`, the `pull` target is never written to the generated `*Targets.cmake` file. CMake configure fails immediately. | Each `prometheus-cpp::*` CMake target depends on the matching `with_*` Conan option. Mismatch → configure error before any compilation. |
| 2 | Linked only `prometheus-cpp::pull` in the main library but omitted it from test fixtures | Test fixtures that include `metrics.hpp` transitively (via `store.hpp`) had no prometheus-cpp in their link graph. Compile error: Prometheus headers not found. | Header dependencies are transitive. Every CMake target that includes a Prometheus type needs the dep in its link tree — either directly or via a `PUBLIC` link from an upstream target. |
| 3 | Switched all callers to use text serializer (correct approach) but still linked `prometheus-cpp::pull` | Build still failed — `pull` target does not exist when option is off, regardless of which symbols you use | The text-format serializer (`TextSerializer`) lives in `prometheus-cpp::core`, not `::pull`. Linking `::pull` to access `::core` symbols doesn't work when `::pull` is absent. |

## Results & Parameters

### Component / Option / Target Mapping

| Goal | Conan option | CMake target |
|------|--------------|--------------|
| Emit metrics as text (GET /metrics, most common) | `with_pull=False` (or any) | `prometheus-cpp::core` |
| Embedded HTTP pull server | `with_pull=True` | `prometheus-cpp::pull` |
| Push to Prometheus pushgateway | `with_push=True` | `prometheus-cpp::push` |
| gzip compression of metrics output | `with_compression=True` | `prometheus-cpp::core` (still core) |

### Diagnosing Which Target Contains a Symbol

```bash
# Find which prometheus-cpp CMake targets expose a given symbol/header
find $CONAN_HOME/data/prometheus-cpp -name "*Targets.cmake" -exec grep -l "<symbol>" {} \;

# Or list all generated targets in the active build
find . -path "*/conan*" -name "*.cmake" | xargs grep "prometheus-cpp::" 2>/dev/null | sort -u
```

### PUBLIC vs PRIVATE linking

```cmake
# In the library that owns the metrics types:
add_library(agamemnon_lib STATIC store.cpp metrics.cpp)
target_link_libraries(agamemnon_lib PUBLIC prometheus-cpp::core)
#                                   ^^^^^^ PUBLIC propagates to consumers

# Test fixture — automatically gets prometheus-cpp::core via agamemnon_lib's PUBLIC deps:
add_executable(agamemnon_tests test_main.cpp)
target_link_libraries(agamemnon_tests PRIVATE agamemnon_lib GTest::gtest_main)
# No explicit prometheus-cpp::core needed here because agamemnon_lib exports it publicly
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectAgamemnon | PR #292 — Prometheus metrics feature | Build went green after switching from `::pull` to `::core` and adding `PUBLIC` propagation |
