---
name: cpp-clang-tidy-deps-header-filter-fix
description: "Fix clang-tidy HeaderFilterRegex accidentally matching FetchContent _deps/ third-party headers. Use when: (1) clang-tidy CI floods warnings from _deps/ vendor headers, (2) HeaderFilterRegex uses bare directory names like src/ that match _deps/*/src/ paths, (3) ExcludeHeaderFilterRegex causes unknown key errors in older clang-tidy, (4) -llvm-* suppressor does not silence llvmlibc-* checks."
category: ci-cd
date: 2026-04-07
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - clang-tidy
  - cmake
  - fetchcontent
  - cpp
  - header-filter
  - static-analysis
  - ci-cd
---

# clang-tidy HeaderFilterRegex Matching _deps/ Third-Party Headers

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-07 |
| **Objective** | Stop clang-tidy from reporting warnings from FetchContent _deps/ vendor headers |
| **Outcome** | clang-tidy CI passes after anchoring HeaderFilterRegex to project name |
| **Verification** | verified-ci |

## When to Use

- clang-tidy CI flooded with warnings from third-party headers in `_deps/` (FetchContent)
- `.clang-tidy` has `HeaderFilterRegex: '(include|src|test)/'` and project uses FetchContent
- `ExcludeHeaderFilterRegex: '_deps/'` causes "unknown key" clang-tidy error
- `-llvm-*` in Checks does not suppress `llvmlibc-restrict-system-libc-headers` warnings
- Warnings appear from paths like `_deps/nats_c-src/src/nats.h` or `_deps/*/src/*.h`

## Verified Workflow

### Quick Reference

```yaml
# In .clang-tidy — anchor HeaderFilterRegex to project name:
Checks: >
  *,
  -fuchsia-*,
  -llvm-*,
  -llvmlibc-*,
  ...other suppressions...
WarningsAsErrors: ''
HeaderFilterRegex: '/ProjectName/(include|src|test)/'
FormatStyle: file
```

### Detailed Steps

1. Open `.clang-tidy` in the repo root
2. Change `HeaderFilterRegex` from bare directory pattern to project-anchored:
   - Before: `HeaderFilterRegex: '(include|src|test)/'`
   - After: `HeaderFilterRegex: '/YourProjectName/(include|src|test)/'`
   - The project name anchor prevents matching `_deps/nats_c-src/src/` paths
3. Add `-llvmlibc-*` to the Checks suppressor list if `llvmlibc-*` warnings appear
4. Do NOT use `ExcludeHeaderFilterRegex` — causes "unknown key" parse error on system clang-tidy (Ubuntu 24.04)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| ExcludeHeaderFilterRegex | Added `ExcludeHeaderFilterRegex: '_deps/'` to .clang-tidy | "unknown key 'ExcludeHeaderFilterRegex'" — not supported in older clang-tidy | Use anchored HeaderFilterRegex instead |
| Bare directory regex | `HeaderFilterRegex: '(include|src|test)/'` | Matches `_deps/nats_c-src/src/nats.h` because the path contains `/src/` | Must anchor to project root, not just directory name |
| Only -llvm-* suppressor | Expected -llvm-* to cover all llvm-prefixed checks | `llvmlibc-*` checks still fire | The `llvmlibc-*` family has a different prefix — add `-llvmlibc-*` separately |

## Results & Parameters

```yaml
# Correct .clang-tidy configuration for a project named "ProjectAgamemnon":
---
Checks: >
  *,
  -fuchsia-*,
  -llvm-*,
  -llvmlibc-*,
  -google-readability-todo,
  -readability-magic-numbers,
  -cppcoreguidelines-avoid-magic-numbers,
  -modernize-use-trailing-return-type,
  -altera-*,
  -cert-err58-cpp,
  -cppcoreguidelines-pro-bounds-array-to-pointer-decay,
  -hicpp-no-array-decay
WarningsAsErrors: ''
HeaderFilterRegex: '/ProjectAgamemnon/(include|src|test)/'
FormatStyle: file
...

# GitHub Actions ubuntu-24.04 runner path examples:
# MATCHED:     /home/runner/work/ProjectAgamemnon/ProjectAgamemnon/include/...
# NOT MATCHED: /home/runner/work/ProjectAgamemnon/ProjectAgamemnon/build/debug/_deps/nats_c-src/src/nats.h
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectAgamemnon | clang-tidy CI check FAILURE to SUCCESS | Anchored HeaderFilterRegex + added -llvmlibc-* suppressor |
| ProjectNestor | Same fix applied, CI passes | Identical pattern — same FetchContent nats.c dependency |
