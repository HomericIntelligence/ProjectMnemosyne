---
name: cpp-conflict-resolution-clang-format-cmake-and-local-build
description: "Avoid breaking the build during a C++ rebase/merge conflict resolution: NEVER run clang-format on non-C++ files (it silently mangles CMakeLists.txt into a CMake parse error), and build the resolved merge LOCALLY before pushing to catch sibling-PR signature changes. Use when: (1) resolving a rebase/merge conflict that touches both C++ and CMakeLists/*.cmake/*.yaml; (2) clang-format ran on a build/config file and CI now fails with a CMake `Parse error`/`Expected a newline`; (3) `include(cmake / X.cmake)` with stray spaces around `/` appears after formatting; (4) you hand-resolved a conflict in compiled code and want to verify it before a slow CI round; (5) a sibling PR changed a function signature and your call sites (including tests) fail with 'too few/many arguments' after rebase."
category: tooling
date: 2026-06-02
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - clang-format
  - cmake
  - rebase
  - conflict
  - local-build
---

# C++ Conflict Resolution: clang-format vs CMake, and Build-Before-Push

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-02 |
| **Objective** | Resolve a non-trivial C++ rebase conflict cleanly without breaking the build, and verify the resolution before a slow CI round-trip |
| **Outcome** | Successful — the next CI run passed (ubuntu-24.04-gcc-release + integration-tests green) and the PR merged to main (ProjectNestor #101, HEAD 56d3ec8) |
| **Verification** | verified-ci |

Two tightly-coupled lessons, same search surface ("my conflict-resolution edit broke the build / verify before pushing"):

- **Lesson A** — `clang-format` is a C/C++/Java/JS formatter only. Pointing it at `CMakeLists.txt` (or any non-C-family file) silently rewrites it into syntactic garbage and causes a CMake CONFIGURE-time parse error — NOT a compile error, and NOT in the file you'd suspect.
- **Lesson B** — When you hand-resolve a conflict in compiled code, a single LOCAL build via the repo's own recipe surfaces ALL errors at once (CMake parse error, then a sibling-PR signature mismatch in a test), whereas CI surfaces them one slow round at a time.

## When to Use

- Resolving a rebase/merge conflict that touches BOTH C++ sources and a build/config file (`CMakeLists.txt`, `*.cmake`, `*.yaml`, `*.toml`, `justfile`).
- `clang-format` was run on a build/config file and CI now fails at CMake configure with a `Parse error` / `Expected a newline`.
- After formatting you see `include(cmake / StandardSettings.cmake)` with stray spaces around the `/`, or a `project(...)`/`if()...endif()` block broken across malformed lines.
- You hand-resolved a conflict in compiled code and want to verify it locally before spending a slow CI round (~3-5 min) per error.
- A sibling PR changed a shared function SIGNATURE and your branch's call sites (including tests) haven't caught up, producing "too few/many arguments to function" after rebase.

## Verified Workflow

### Quick Reference

```bash
# --- Lesson A: clang-format ONLY the C/C++ files you edited, BY NAME. Never a build file. ---
# GOOD — explicit C/C++ files only:
clang-format -i src/server_main.cpp src/tls_config.cpp
# BAD — mangles the CMake file into a parse error:
#   clang-format -i src/server_main.cpp CMakeLists.txt   # <-- NEVER

# --- Additive CMakeLists conflict: take main's correctly-formatted version verbatim, ---
# --- then insert ONLY the PR's new source lines after a stable anchor. No formatter touches it. ---
git show origin/main:CMakeLists.txt \
  | sed 's|^  src/rate_limiter.cpp$|  src/rate_limiter.cpp\n  src/tls_config.cpp\n  src/security_warnings.cpp|' \
  > CMakeLists.txt

# --- Lesson B: build the resolved merge LOCALLY before pushing; surface ALL errors at once ---
just build 2>&1 | grep -iE "error|Parse error|too few|too many|FAILED" || echo "BUILD CLEAN"
# Only after a clean local build: clang-format the touched C++, amend, sign, push.
git commit --amend -S --no-edit
git push --force-with-lease
```

### Detailed Steps

1. **Resolve the C++ conflicts by hand** in the actual source/header files. Note exactly which `.cpp`/`.h` files you touched.
2. **Resolve the build-file conflict by hand — do NOT format it.** For an additive conflict (both sides add source files to the same `add_library`/`add_executable` block), regenerate from main and re-insert only the PR's added lines:
   ```bash
   git show origin/main:CMakeLists.txt \
     | sed 's|^  <stable-anchor-line>$|  <stable-anchor-line>\n  <pr-added-line-1>\n  <pr-added-line-2>|' \
     > CMakeLists.txt
   ```
   This takes main's correctly-formatted version verbatim and keeps the formatter away.
3. **clang-format ONLY the C/C++ files, listed explicitly by name.** Never pass `CMakeLists.txt`, `*.cmake`, `*.yaml`, `*.toml`, `*.md`, or `justfile` to clang-format. (If you genuinely must format CMake, use `gersemi` or `cmake-format` — but for a conflict resolution, leave its formatting alone.)
4. **Build locally via the repo's own recipe BEFORE pushing:** `just build` / `pixi run build` / the cmake preset. Grep the output for `error`/`Parse error`/`too few`/`too many`/`FAILED`. One local build catches the CMake parse error AND any sibling-PR signature mismatch (including in tests) in a single pass.
5. **Fix every error surfaced**, rebuild until both library and test targets link, e.g. `[2/4] Linking <proj>_server` and `[4/4] Linking <proj>_tests` both succeed.
6. **Only then** amend, sign (`-S`), and push. The next CI run should pass on the first try.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Ran `clang-format -i src/server_main.cpp CMakeLists.txt` to "tidy" resolved files during the rebase | clang-format does not understand CMake syntax; it broke `project(...)` across lines, mangled `if()/endif()`, and turned `include(cmake/StandardSettings.cmake)` into `include(cmake / StandardSettings.cmake)`. CI failed at CMake CONFIGURE time: `CMake Error at CMakeLists.txt:7: Parse error. Expected a newline, got identifier with text "message".` — not a compile error and not in server_main.cpp. Wasted a full CI round. | clang-format is C/C++/Java/JS only. During conflict resolution, only ever format the actual C/C++ files you edited, listed by name. Never pass build/config files to it; resolve CMake by hand or regenerate from origin/main. |
| 2 | Pushed the hand-resolved merge straight to CI without building it locally | CI compile failed in `test/src/test_server_tls.cpp:111`: it still called the OLD 3-arg `register_routes(*ssl_server_, store_, nats_)`, but a sibling PR merged to main had changed the signature to 4-arg `register_routes(..., RateLimiter& limiter)` → `too few arguments to function 'void register_routes(..., RateLimiter&)'`. CI surfaces one error per slow round. | When hand-resolving a non-trivial conflict in compiled code, build it locally via the repo's own recipe first. One local build surfaces every error at once — especially when a sibling PR changed a shared function signature your call sites (incl. tests) haven't caught up to. |

## Results & Parameters

**Exact CMake CONFIGURE-time error from the clang-format mangling:**

```
CMake Error at CMakeLists.txt:7:
  Parse error.  Expected a newline, got identifier with text "message".
```

Tell-tale mangled artifact in the file:

```cmake
include(cmake / StandardSettings.cmake)   # stray spaces around "/" — clang-format did this
```

**Additive-merge recipe (take main verbatim, insert only the PR's new sources after a stable anchor):**

```bash
git show origin/main:CMakeLists.txt \
  | sed 's|^  src/rate_limiter.cpp$|  src/rate_limiter.cpp\n  src/tls_config.cpp\n  src/security_warnings.cpp|' \
  > CMakeLists.txt
```

**Local-build-before-push, grepping for all errors at once:**

```bash
just build 2>&1 | grep -iE "error|Parse error|too few|too many|FAILED" || echo "BUILD CLEAN"
```

Expected clean tail after fixes (both targets link):

```
[2/4] Linking ProjectNestor_server
[4/4] Linking ProjectNestor_tests
```

**Sibling-PR signature mismatch error (caught locally, not in CI):**

```
test/src/test_server_tls.cpp:111: error: too few arguments to function
  'void register_routes(..., RateLimiter&)'
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectNestor | PR #101 final rebase — clang-format CMake mangling caused a real CI parse-error failure; the local-build-before-push fix produced a passing CI run (ubuntu-24.04-gcc-release + integration-tests green) that merged to main (HEAD 56d3ec8, 2026-06-02) | — |
